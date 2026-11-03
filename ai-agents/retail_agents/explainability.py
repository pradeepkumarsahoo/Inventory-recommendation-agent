"""Explainability: evidence-backed recommendation decoration.

Takes a raw `Recommendation.to_dict()` and wraps it with:

- **Evidence references**: a list of {source, timestamp, metric, value}
  tuples the recommendation was built from.
- **Scoring breakdown**: component weights and contributions, so a
  reviewer can see WHY the composite score landed where it did.
- **Confidence rationale**: a human-readable sentence explaining the
  confidence number.
- **Decision summary**: the five questions every recommendation must
  answer (why, what supports it, what's the impact, confidence,
  what could go wrong) assembled into a single, consumable block.

The output of `explain()` is still JSON — a UI can render each field
however it wants, and the HTML report can lift the `decision_summary`
block verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class EvidenceRef:
    source: str                 # "sales_90d" | "inventory_snapshot" | "trends_latest" | ...
    metric: str                 # "weekly_velocity" | "age_days" | ...
    value: Any
    recorded_at: str            # ISO timestamp of the underlying data

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "metric": self.metric,
            "value": self.value,
            "recorded_at": self.recorded_at,
        }


def _confidence_rationale(confidence: float, risks: list[str]) -> str:
    if confidence >= 0.85:
        band = "high confidence — multiple strong signals align"
    elif confidence >= 0.65:
        band = "moderate confidence — most signals align, residual uncertainty"
    else:
        band = "low confidence — weak signal mix, treat as suggestion"
    if risks:
        band += f"; {len(risks)} named risk(s) tracked"
    return band


# ---------- Scoring breakdown ----------------------------------------------

FRONT_OFFICE_WEIGHTS = {
    "velocity": 0.30, "margin": 0.25, "demand": 0.20,
    "sentiment": 0.15, "availability": 0.10,
}


def _front_office_breakdown(metrics: dict) -> list[dict]:
    """Return per-component contribution. Metrics are normalized at
    ranking time; here we just surface what each dimension looks like."""
    out = []
    for component, weight in FRONT_OFFICE_WEIGHTS.items():
        key = {
            "velocity": "weekly_velocity",
            "margin": "gross_margin_percent",
            "demand": "demand_signal",
            "sentiment": "avg_satisfaction",
            "availability": "on_hand_quantity",
        }.get(component)
        raw = metrics.get(key)
        if raw is None:
            continue
        out.append({
            "component": component,
            "weight": weight,
            "raw_value": raw,
            "notes": f"Weighted {weight * 100:.0f}% of composite score.",
        })
    return out


# ---------- Evidence assembly ----------------------------------------------

def _collect_evidence(recommendation: dict, data_timestamp: str) -> list[EvidenceRef]:
    metrics = recommendation.get("supporting_metrics", {})
    action = recommendation.get("action_type", "")
    evidence: list[EvidenceRef] = []

    if "weekly_velocity" in metrics:
        evidence.append(EvidenceRef("sales_90d", "weekly_velocity",
                                     metrics["weekly_velocity"], data_timestamp))
    if "gross_margin_percent" in metrics:
        evidence.append(EvidenceRef("sales_90d", "gross_margin_percent",
                                     metrics["gross_margin_percent"], data_timestamp))
    if "on_hand_quantity" in metrics:
        evidence.append(EvidenceRef("inventory_snapshot", "on_hand_quantity",
                                     metrics["on_hand_quantity"], data_timestamp))
    if "age_days" in metrics:
        evidence.append(EvidenceRef("inventory_snapshot", "age_days",
                                     metrics["age_days"], data_timestamp))
    if "demand_signal" in metrics:
        evidence.append(EvidenceRef("trends_latest", "demand_signal_score",
                                     metrics["demand_signal"], data_timestamp))
    if "avg_satisfaction" in metrics:
        evidence.append(EvidenceRef("surveys", "avg_satisfaction",
                                     metrics["avg_satisfaction"], data_timestamp))
    if "return_rate" in metrics:
        evidence.append(EvidenceRef("returns", "return_rate",
                                     metrics["return_rate"], data_timestamp))
    return evidence


# ---------- Public API ------------------------------------------------------

def explain(recommendation: dict,
            data_timestamp: str | None = None) -> dict:
    """Attach explainability block to a single recommendation.

    Returns a NEW dict; the input is not mutated.
    """
    ts = data_timestamp or datetime.utcnow().isoformat()
    evidence = _collect_evidence(recommendation, ts)
    action = recommendation.get("action_type", "")
    confidence = float(recommendation.get("confidence", 0.0))

    breakdown = (_front_office_breakdown(recommendation.get("supporting_metrics", {}))
                 if action == "FRONT_OFFICE" else [])

    decision_summary = {
        "why": recommendation.get("justification", ""),
        "evidence": [e.to_dict() for e in evidence],
        "expected_impact": {
            "revenue": recommendation.get("expected_sales_impact"),
            "margin": recommendation.get("expected_margin_impact"),
            "deadline_hours": recommendation.get("deadline_hours"),
            "success_kpi": recommendation.get("success_kpi"),
        },
        "confidence": confidence,
        "confidence_rationale": _confidence_rationale(confidence,
                                                      recommendation.get("risks", [])),
        "what_could_go_wrong": recommendation.get("risks", []),
        "assumptions": recommendation.get("assumptions", []),
        "approval_required": recommendation.get("required_approval"),
    }

    out = dict(recommendation)
    out["explainability"] = {
        "decision_summary": decision_summary,
        "scoring_breakdown": breakdown,
        "data_timestamp": ts,
        "schema_version": "1.0",
    }
    return out


def explain_all(recommendations: list[dict],
                data_timestamp: str | None = None) -> list[dict]:
    return [explain(r, data_timestamp) for r in recommendations]
