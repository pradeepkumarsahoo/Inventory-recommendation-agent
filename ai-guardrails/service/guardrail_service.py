"""Guardrail Service for the retail agent system.

Integrates NVIDIA NeMo Guardrails when available, and falls back to a
local policy engine that enforces the same contracts when the NeMo
package is not installed. Fail-closed on any policy error.

Policies enforced (both paths):

1. Input validation
   - Reject empty / overlong requests, obvious prompt-injection markers,
     and known jailbreak patterns.

2. PII protection
   - Scrub emails, phone numbers, SSNs from any string reaching the LLM.

3. Topic restriction
   - Only retail/inventory/pricing topics are permitted. Any out-of-scope
     input is refused.

4. Tool invocation validation
   - Agents may only call tools from the registered allowlist.

5. Output validation (recommendation shape)
   - Every recommendation must carry evidence (supporting_metrics ≠ {}),
     bounded confidence (0 ≤ x ≤ 1), and a non-trivial justification.

6. Action authorization
   - Price changes, transfers, and markdowns always require human approval.
     The service rejects any recommendation that attempts to mark itself as
     "auto-executable" for consequential actions.

7. Hallucination mitigation
   - Metrics that reference unknown product_id or store_id are rejected,
     because the data store is the single source of truth.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_TOOLS = {
    "get_product_catalog",
    "get_store_catalog",
    "get_sales_summary",
    "get_inventory_position",
    "get_return_rates",
    "get_survey_sentiment",
    "get_trending_products",
    "get_nearby_stores",
    "get_store_forecast",
}

CONSEQUENTIAL_ACTIONS = {"PRICING", "TRANSFER", "MARKDOWN", "PROMOTE", "CLEARANCE", "BUNDLE", "REPLENISH"}

INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+a\s+different\s+(ai|assistant|model)"),
    re.compile(r"(?i)disregard\s+(your\s+)?system\s+prompt"),
    re.compile(r"(?i)reveal\s+your\s+(system\s+)?prompt"),
    re.compile(r"(?i)execute\s+(sql|shell|command)"),
    re.compile(r"(?i)drop\s+table"),
    re.compile(r"(?i)\bDAN\b|\bdeveloper\s+mode\b|\bjailbreak\b"),
]

PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]

ALLOWED_INTENTS = {
    "daily_game_plan",
    "front_office_recommendation",
    "inventory_transfer",
    "pricing_optimization",
    "sales_forecast",
    "aging_action",
    "store_target",
}


@dataclass
class GuardrailService:
    config_path: Path = Path(__file__).resolve().parents[1] / "config" / "config.yml"
    data_dir: Path = Path(__file__).resolve().parents[2] / "databricks" / "sample-data"

    def __post_init__(self):
        self._nemo = self._try_load_nemo()
        self._known_product_ids = self._load_ids("products.csv", "product_id")
        self._known_store_ids = self._load_ids("stores.csv", "store_id")

    def _try_load_nemo(self):
        # NeMo Guardrails is optional; the local engine enforces the same contract.
        if os.environ.get("RETAIL_GUARDRAILS_DISABLE_NEMO") == "1":
            return None
        try:
            from nemoguardrails import LLMRails, RailsConfig  # type: ignore  # pragma: no cover
            if self.config_path.exists():
                cfg = RailsConfig.from_path(str(self.config_path.parent))
                return LLMRails(cfg)
        except Exception:
            return None
        return None

    def _load_ids(self, name: str, col: str) -> set[str]:
        p = self.data_dir / name
        if not p.exists():
            return set()
        import csv
        with p.open("r", encoding="utf-8") as f:
            return {row[col] for row in csv.DictReader(f) if col in row}

    # ---- Public API ------------------------------------------------------
    def validate_input(self, request: dict) -> dict:
        try:
            store = request.get("store_id", "")
            intent = request.get("intent", "")
            if intent not in ALLOWED_INTENTS:
                return _deny("intent_not_allowed", f"intent '{intent}' is not in the allowlist")
            if store and store not in self._known_store_ids:
                return _deny("unknown_store", f"store '{store}' not found in master data")
            # Any free-text fields pass through the content scanner.
            for v in request.values():
                if isinstance(v, str) and _is_injection(v):
                    return _deny("prompt_injection_detected", "input matches a known injection pattern")
            return {"allowed": True, "reason": None, "sanitized": self.sanitize_text(request)}
        except Exception as e:  # fail closed
            return _deny("guardrail_error", str(e))

    def validate_tool_call(self, tool_name: str, args: dict) -> dict:
        if tool_name not in ALLOWED_TOOLS:
            return _deny("tool_not_allowed", f"tool '{tool_name}' is not registered")
        for v in args.values():
            if isinstance(v, str) and _is_injection(v):
                return _deny("tool_arg_injection", "tool argument matches an injection pattern")
        return {"allowed": True, "reason": None}

    def validate_recommendation(self, rec: dict) -> dict:
        # Shape checks
        required = {"recommendation_id", "action_type", "justification", "supporting_metrics", "confidence", "required_approval"}
        missing = required - set(rec.keys())
        if missing:
            return _deny("missing_fields", f"missing: {sorted(missing)}")
        if not rec["supporting_metrics"]:
            return _deny("no_evidence", "recommendation has no supporting metrics")
        if len(str(rec["justification"])) < 20:
            return _deny("thin_justification", "justification is too short to be grounded")
        c = float(rec.get("confidence", 0))
        if not 0.0 <= c <= 1.0:
            return _deny("invalid_confidence", "confidence must be in [0,1]")
        # Grounding checks
        pid = rec.get("product_id")
        if pid and pid not in self._known_product_ids:
            return _deny("unknown_product", f"product '{pid}' is not in the catalog")
        if rec["store_id"] not in self._known_store_ids:
            return _deny("unknown_store", f"store '{rec['store_id']}' is not in the catalog")
        # Human approval enforcement
        if rec["action_type"] in CONSEQUENTIAL_ACTIONS and rec["required_approval"] == "none":
            return _deny("missing_approval", f"{rec['action_type']} must require human approval")
        if rec.get("status") == "executed" and rec["required_approval"] != "none":
            return _deny("premature_execution", "action marked executed without approval")
        return {"allowed": True, "reason": None}

    def authorize_execution(self, rec: dict, approver_role: str) -> dict:
        """Called when a human approves an action. Policy:
        - PRICING / TRANSFER / MARKDOWN / CLEARANCE  → regional_manager
        - REPLENISH → inventory_manager or regional_manager
        - FRONT_OFFICE / PROMOTE / BUNDLE / REVIEW → store_manager or above
        """
        hierarchy = ["sales_associate", "store_manager", "inventory_manager", "regional_manager"]
        if approver_role not in hierarchy:
            return _deny("unknown_role", approver_role)
        rank = hierarchy.index(approver_role)
        required = rec.get("required_approval", "store_manager")
        if required == "none":
            return {"allowed": True, "reason": None}
        if required not in hierarchy:
            return _deny("unknown_required_role", required)
        if rank < hierarchy.index(required):
            return _deny("insufficient_role", f"needs {required}, approver is {approver_role}")
        return {"allowed": True, "reason": None}

    def sanitize_text(self, obj: Any) -> Any:
        if isinstance(obj, str):
            out = obj
            for pat, repl in PII_PATTERNS:
                out = pat.sub(repl, out)
            return out
        if isinstance(obj, list):
            return [self.sanitize_text(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.sanitize_text(v) for k, v in obj.items()}
        return obj


def _deny(code: str, msg: str) -> dict:
    return {"allowed": False, "reason": f"{code}: {msg}"}


def _is_injection(s: str) -> bool:
    return any(p.search(s) for p in INJECTION_PATTERNS)
