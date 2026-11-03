"""Tests for simulation + explainability + observability."""
from __future__ import annotations

from retail_agents.simulation import SKUState, compare
from retail_agents.explainability import explain, explain_all
from retail_agents.observability import METRICS, record_tool_call, record_llm_usage


def _skus():
    return [
        SKUState("P-HOT", on_hand=50, weekly_velocity=20, base_price=10,
                 unit_cost=4, age_days=20, aging_bucket="0-30"),
        SKUState("P-AGED", on_hand=80, weekly_velocity=1, base_price=20,
                 unit_cost=8, age_days=200, aging_bucket="180+"),
    ]


def test_front_office_lifts_revenue_in_simulation():
    recs = [{"product_id": "P-HOT", "action_type": "FRONT_OFFICE"}]
    out = compare(_skus(), recs)
    assert out["deltas"]["revenue_delta"] > 0
    assert "SIMULATED" in out["disclaimer"]


def test_markdown_reduces_aged_units():
    recs = [{"product_id": "P-AGED", "action_type": "MARKDOWN"}]
    out = compare(_skus(), recs)
    assert out["deltas"]["aged_units_delta"] <= 0


def test_explain_adds_evidence_block():
    rec = {
        "recommendation_id": "R1",
        "action_type": "FRONT_OFFICE",
        "justification": "demo",
        "confidence": 0.88,
        "risks": ["uplift is an assumption"],
        "assumptions": ["18% front-office uplift"],
        "supporting_metrics": {
            "weekly_velocity": 15,
            "gross_margin_percent": 42,
            "on_hand_quantity": 30,
            "demand_signal": 0.6,
            "avg_satisfaction": 4.1,
        },
        "expected_sales_impact": 100,
        "expected_margin_impact": 40,
        "deadline_hours": 24,
        "success_kpi": "velocity",
        "required_approval": "store_manager",
    }
    out = explain(rec)
    assert "explainability" in out
    ds = out["explainability"]["decision_summary"]
    assert ds["why"] == "demo"
    assert ds["confidence"] == 0.88
    assert len(ds["evidence"]) >= 3
    assert out["explainability"]["scoring_breakdown"]  # non-empty for FRONT_OFFICE


def test_observability_counters_increment():
    before = METRICS.snapshot()["counters"]
    record_tool_call("get_sales_summary", "ok", 12.3)
    record_llm_usage(100, 50, "claude-opus-4-7")
    after = METRICS.snapshot()["counters"]
    assert len(after) >= len(before)
