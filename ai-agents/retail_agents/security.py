"""Security + data-governance layer for the agent system.

Adds:

- **Row-level store ACLs**: a principal can only read data for stores it is
  granted access to; the ToolRegistry refuses `store_id` arguments outside
  the allowed set.
- **PII masking**: survey comments and customer identifiers are redacted
  before leaving the tool boundary so an LLM never sees them in cleartext.
- **Prompt-injection detection**: common patterns ("ignore previous
  instructions", "system:", role takeover) are flagged on any user-provided
  string before it reaches the LLM.
- **Tool authorization**: each principal has an allow-list of tool names.
- **Secrets handling**: a thin wrapper around environment variables that
  never echoes a key back to the caller and masks it in trace output.
- **Audit of sensitive operations**: every allow/deny decision is logged.

The implementation is intentionally pure-Python so it runs in CI alongside
the existing guardrail service without requiring Vault/KMS integrations.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------- Principals & ACLs ----------------------------------------------

@dataclass
class Principal:
    user_id: str
    role: str                          # "store_manager" | "regional_manager" | "service"
    allowed_stores: set[str] = field(default_factory=set)   # empty = all stores
    allowed_tools: set[str] = field(default_factory=set)    # empty = all tools


SERVICE_PRINCIPAL = Principal(user_id="agent-service", role="service")


def can_access_store(principal: Principal, store_id: str) -> bool:
    if not principal.allowed_stores:
        return True
    return store_id in principal.allowed_stores


def can_use_tool(principal: Principal, tool_name: str) -> bool:
    if not principal.allowed_tools:
        return True
    return tool_name in principal.allowed_tools


# ---------- PII masking -----------------------------------------------------

_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){1,2}\d{3}[-.\s]?\d{4}\b"),
    "ssn":   re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "card":  re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "customer_id": re.compile(r"\bCUST[-_]?\d{4,}\b"),
}


def mask_pii(value: Any) -> Any:
    """Recursively mask PII patterns in strings; leaves other types alone."""
    if isinstance(value, str):
        out = value
        for name, pat in _PII_PATTERNS.items():
            out = pat.sub(f"[REDACTED-{name.upper()}]", out)
        return out
    if isinstance(value, dict):
        return {k: mask_pii(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_pii(v) for v in value]
    return value


# ---------- Prompt injection detection --------------------------------------

_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"disregard\s+(?:all\s+)?(?:prior|above|previous)\s+(?:instructions|context|rules)",
    r"system\s*:\s*you\s+are",
    r"act\s+as\s+(?:an?\s+)?(?:admin|developer|root|superuser)",
    r"reveal\s+(?:your\s+)?system\s+prompt",
    r"</s>\s*<s>|<\|im_start\|>|<\|im_end\|>",       # chat-template tokens
    r"BEGIN\s+NEW\s+INSTRUCTIONS",
    r"print\s+(?:the\s+)?(?:api[_-]?key|secret|token|password)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


@dataclass
class InjectionCheck:
    allowed: bool
    reason: Optional[str] = None
    matches: list[str] = field(default_factory=list)


def detect_prompt_injection(text: str) -> InjectionCheck:
    if not text:
        return InjectionCheck(allowed=True)
    matches = _INJECTION_RE.findall(text)
    if matches:
        return InjectionCheck(
            allowed=False,
            reason="prompt_injection_pattern",
            matches=[str(m) for m in matches],
        )
    return InjectionCheck(allowed=True)


# ---------- Secrets handling -----------------------------------------------

class SecretsManager:
    """Thin wrapper that reads secrets from env vars and never echoes them.

    In production this would wrap AWS Secrets Manager / HashiCorp Vault /
    Azure Key Vault; the interface is kept small so a real backend can be
    dropped in without touching callers.
    """

    SENSITIVE_SUFFIXES = ("API_KEY", "SECRET", "TOKEN", "PASSWORD")

    def get(self, name: str) -> Optional[str]:
        return os.environ.get(name)

    def require(self, name: str) -> str:
        v = self.get(name)
        if not v:
            raise RuntimeError(f"Required secret missing: {name}")
        return v

    @classmethod
    def mask_for_log(cls, env: dict[str, str]) -> dict[str, str]:
        out = {}
        for k, v in env.items():
            if any(k.upper().endswith(suf) for suf in cls.SENSITIVE_SUFFIXES):
                out[k] = f"<masked:{len(v)}c>"
            else:
                out[k] = v
        return out


# ---------- Audit log for sensitive operations ------------------------------

_AUDIT: list[dict] = []


def audit(actor: Principal, action: str, resource: str,
          decision: str, reason: str = "") -> None:
    _AUDIT.append({
        "timestamp": datetime.utcnow().isoformat(),
        "actor": actor.user_id,
        "role": actor.role,
        "action": action,
        "resource": resource,
        "decision": decision,
        "reason": reason,
    })


def get_audit_log() -> list[dict]:
    return list(_AUDIT)


# ---------- Tool-call authorization wrapper ---------------------------------

def authorize_tool_call(
    principal: Principal,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[bool, str]:
    """Return (allowed, reason) for a tool call under this principal.

    The decision is also written to the audit log so downstream reviewers
    can replay who got what.
    """
    if not can_use_tool(principal, tool_name):
        audit(principal, "tool_call", tool_name, "deny", "tool_not_allowed")
        return False, "tool_not_allowed"

    store_id = arguments.get("store_id")
    if store_id and not can_access_store(principal, store_id):
        audit(principal, "tool_call", f"{tool_name}:{store_id}", "deny", "store_acl")
        return False, f"store_acl_denied:{store_id}"

    for key, value in arguments.items():
        if isinstance(value, str):
            check = detect_prompt_injection(value)
            if not check.allowed:
                audit(principal, "tool_call", tool_name, "deny",
                      f"injection:{key}:{check.matches[0]}")
                return False, f"prompt_injection:{key}"

    audit(principal, "tool_call", tool_name, "allow", "")
    return True, "ok"


def guarded_call(
    principal: Principal,
    tool_name: str,
    arguments: dict[str, Any],
    invoker: Callable[..., Any],
) -> Any:
    """Authorize → invoke → PII-mask the result before returning."""
    allowed, reason = authorize_tool_call(principal, tool_name, arguments)
    if not allowed:
        raise PermissionError(f"{tool_name}: {reason}")
    result = invoker(**arguments)
    return mask_pii(result)
