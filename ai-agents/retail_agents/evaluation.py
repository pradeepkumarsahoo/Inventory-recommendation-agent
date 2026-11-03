"""Recommendation accuracy and evaluation framework.

Every production decision system needs to know how good it is. This
module provides:

- A **golden dataset** of hand-labelled retail scenarios (expected
  recommendations for a given input state).
- **Classification metrics** (precision, recall, F1) over whether the
  agent recommended the right ACTION_TYPE for each labelled scenario.
- **Forecast error metrics** (WAPE, MAPE, bias) for the 7-day sales
  forecast against held-out ground truth.
- **Business-constraint checks** (margin floors, approval tiers,
  deadline presence) applied to every emitted recommendation.
- A **false-positive counter** that catches obviously-wrong actions
  (e.g. markdown on a hot seller, transfer when source is also low).

All metrics are deterministic and dependency-free so the regression
suite can trend them over time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any


# ---------- Metrics ---------------------------------------------------------

def wape(actuals: list[float], forecasts: list[float]) -> float:
    """Weighted Absolute Percentage Error — robust to zeros, bounded [0, ∞)."""
    if not actuals:
        return 0.0
    num = sum(abs(a - f) for a, f in zip(actuals, forecasts))
    den = sum(abs(a) for a in actuals)
    return round(num / den, 4) if den else 0.0


def mape(actuals: list[float], forecasts: list[float]) -> float:
    """Mean Absolute Percentage Error — unstable near zero, kept for parity."""
    if not actuals:
        return 0.0
    vals = [abs(a - f) / abs(a) for a, f in zip(actuals, forecasts) if a]
    return round(mean(vals), 4) if vals else 0.0


def forecast_bias(actuals: list[float], forecasts: list[float]) -> float:
    """Average (forecast - actual) / actual — positive = over-forecasting."""
    if not actuals:
        return 0.0
    diffs = [(f - a) / a for a, f in zip(actuals, forecasts) if a]
    return round(mean(diffs), 4) if diffs else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn,
    }


# ---------- Golden dataset --------------------------------------------------

@dataclass
class GoldenScenario:
    """A hand-labelled test case: given this situation, this is what the agent SHOULD recommend."""
    scenario_id: str
    description: str
    store_id: str
    product_id: str
    inputs: dict[str, Any]              # inventory/sales/sentiment snapshot
    expected_action_types: set[str]     # one of these must appear
    forbidden_action_types: set[str] = field(default_factory=set)
    notes: str = ""


GOLDEN_SCENARIOS: list[GoldenScenario] = [
    GoldenScenario(
        scenario_id="G001",
        description="Hot seller, strong margin, on-hand sufficient → front-office feature",
        store_id="S101", product_id="P-HOT-01",
        inputs={"weekly_velocity": 18.0, "margin": 0.42, "on_hand": 60, "age_days": 15},
        expected_action_types={"FRONT_OFFICE"},
        forbidden_action_types={"MARKDOWN", "PRICING_DOWN"},
    ),
    GoldenScenario(
        scenario_id="G002",
        description="Dead stock aged 200+ days with low velocity → markdown with approval",
        store_id="S101", product_id="P-DEAD-01",
        inputs={"weekly_velocity": 0.4, "margin": 0.45, "on_hand": 80, "age_days": 215},
        expected_action_types={"MARKDOWN", "AGING_REVIEW"},
        forbidden_action_types={"FRONT_OFFICE", "REPLENISH"},
    ),
    GoldenScenario(
        scenario_id="G003",
        description="Fast mover understocked locally, overstocked nearby → transfer in",
        store_id="S101", product_id="P-IMBAL-01",
        inputs={"local_on_hand": 8, "local_velocity": 14.0,
                "neighbor_on_hand": 140, "neighbor_velocity": 3.0},
        expected_action_types={"TRANSFER", "REPLENISH"},
        forbidden_action_types={"MARKDOWN"},
    ),
    GoldenScenario(
        scenario_id="G004",
        description="Elastic SKU with weeks-of-cover=12, margin healthy → price-down to accelerate",
        store_id="S101", product_id="P-ELAS-01",
        inputs={"weeks_of_cover": 12, "margin": 0.42, "velocity_trend": "flat"},
        expected_action_types={"PRICING", "PRICING_DOWN"},
        forbidden_action_types={"FRONT_OFFICE"},
    ),
    GoldenScenario(
        scenario_id="G005",
        description="Chronic returner (>20%) should never be featured",
        store_id="S101", product_id="P-RETURN-01",
        inputs={"return_rate": 0.28, "velocity": 10.0},
        expected_action_types=set(),       # None required
        forbidden_action_types={"FRONT_OFFICE"},
    ),
]


# ---------- Evaluators ------------------------------------------------------

def evaluate_classification(
    scenarios: list[GoldenScenario],
    agent_outputs: dict[str, list[dict]],
) -> dict[str, Any]:
    """Compare agent recommendations against the expected action types.

    `agent_outputs` is keyed by scenario_id and contains the list of
    recommendation dicts the agent produced for that scenario.
    """
    tp = fp = fn = 0
    per_scenario = []
    for sc in scenarios:
        recs = agent_outputs.get(sc.scenario_id, [])
        emitted = {r.get("action_type") for r in recs}

        hit = bool(sc.expected_action_types & emitted)
        banned_hit = sc.forbidden_action_types & emitted
        if sc.expected_action_types:
            if hit:
                tp += 1
            else:
                fn += 1
        if banned_hit:
            fp += 1

        per_scenario.append({
            "scenario_id": sc.scenario_id,
            "expected": sorted(sc.expected_action_types),
            "forbidden": sorted(sc.forbidden_action_types),
            "emitted": sorted(a for a in emitted if a),
            "status": (
                "ok" if hit and not banned_hit
                else "forbidden_emitted" if banned_hit
                else "miss" if sc.expected_action_types
                else "no_action_expected"
            ),
        })
    metrics = precision_recall_f1(tp, fp, fn)
    return {"metrics": metrics, "per_scenario": per_scenario}


def evaluate_forecast(actual_7d: list[float], forecast_7d: list[float]) -> dict[str, float]:
    return {
        "wape": wape(actual_7d, forecast_7d),
        "mape": mape(actual_7d, forecast_7d),
        "bias": forecast_bias(actual_7d, forecast_7d),
        "n_points": len(actual_7d),
    }


# ---------- Business-constraint checks --------------------------------------

MARGIN_FLOOR_PCT = 10.0


def check_recommendation(rec: dict) -> list[str]:
    """Return a list of violated business constraints for one recommendation."""
    violations: list[str] = []
    if rec.get("action_type") in ("MARKDOWN", "PRICING") and rec.get("required_approval") == "none":
        violations.append("pricing_without_approval")
    metrics = rec.get("supporting_metrics", {})
    projected_margin = metrics.get("projected_margin_percent")
    if projected_margin is not None and projected_margin < MARGIN_FLOOR_PCT:
        violations.append(f"below_margin_floor:{projected_margin}")
    if not rec.get("success_kpi"):
        violations.append("missing_success_kpi")
    if rec.get("deadline_hours") in (None, 0):
        violations.append("missing_deadline")
    return violations


def evaluate_business_constraints(recommendations: list[dict]) -> dict[str, Any]:
    violations_per_rec: list[dict] = []
    for r in recommendations:
        v = check_recommendation(r)
        if v:
            violations_per_rec.append({
                "recommendation_id": r.get("recommendation_id"),
                "violations": v,
            })
    return {
        "total_recommendations": len(recommendations),
        "with_violations": len(violations_per_rec),
        "violation_rate": round(len(violations_per_rec) / len(recommendations), 4)
        if recommendations else 0.0,
        "details": violations_per_rec,
    }


# ---------- False positive detection ----------------------------------------

def detect_false_positives(recommendations: list[dict]) -> list[dict]:
    """Catch obviously wrong actions: markdowns on hot sellers, transfers from
    low-stock stores, pricing-down on sold-out SKUs, etc. These are not
    guardrail blocks — they're a post-hoc sanity layer that an evaluation
    harness surfaces so the specialists can be improved."""
    out: list[dict] = []
    for r in recommendations:
        m = r.get("supporting_metrics", {})
        action = r.get("action_type")
        reason = None

        if action == "MARKDOWN" and m.get("weekly_velocity", 0) >= 15:
            reason = "markdown_on_fast_mover"
        if action == "FRONT_OFFICE" and m.get("return_rate", 0) > 0.20:
            reason = "feature_chronic_returner"
        if action == "TRANSFER" and m.get("source_weeks_of_cover", 99) < 2:
            reason = "transfer_from_low_cover_source"
        if action == "PRICING" and m.get("on_hand_quantity", 1) == 0:
            reason = "price_change_on_zero_stock"

        if reason:
            out.append({
                "recommendation_id": r.get("recommendation_id"),
                "false_positive_reason": reason,
                "action_type": action,
            })
    return out


# ---------- Public entry point ----------------------------------------------

def run_full_evaluation(
    agent_outputs: dict[str, list[dict]],
    recommendations: list[dict],
    actual_7d: list[float] | None = None,
    forecast_7d: list[float] | None = None,
) -> dict[str, Any]:
    """One-shot evaluation report: classification + constraints + false-positives + forecast."""
    report = {
        "classification": evaluate_classification(GOLDEN_SCENARIOS, agent_outputs),
        "business_constraints": evaluate_business_constraints(recommendations),
        "false_positives": detect_false_positives(recommendations),
    }
    if actual_7d and forecast_7d:
        report["forecast"] = evaluate_forecast(actual_7d, forecast_7d)
    report["summary"] = {
        "f1": report["classification"]["metrics"]["f1"],
        "constraint_violation_rate": report["business_constraints"]["violation_rate"],
        "false_positive_count": len(report["false_positives"]),
    }
    return report
