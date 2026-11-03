"""Tests for the evaluation framework."""
from __future__ import annotations

import pytest

from retail_agents.evaluation import (
    wape, mape, forecast_bias, precision_recall_f1,
    evaluate_classification, evaluate_business_constraints,
    detect_false_positives, GOLDEN_SCENARIOS, run_full_evaluation,
)


def test_wape_zero_when_perfect():
    assert wape([10, 20, 30], [10, 20, 30]) == 0.0


def test_wape_matches_formula():
    # |10-12|+|20-18|+|30-33| = 7 ; sum|actual|=60 → 0.1167
    assert wape([10, 20, 30], [12, 18, 33]) == 0.1167


def test_mape_ignores_zero_actuals():
    assert mape([0, 10], [5, 11]) == 0.1


def test_bias_detects_over_forecast():
    assert forecast_bias([10, 10], [11, 11]) == 0.1


def test_precision_recall_f1_basic():
    m = precision_recall_f1(tp=5, fp=2, fn=3)
    assert m["precision"] == pytest.approx(5 / 7, rel=0.01)
    assert m["recall"] == 0.625


def test_classification_hit():
    outputs = {
        "G001": [{"action_type": "FRONT_OFFICE"}],
        "G002": [{"action_type": "MARKDOWN"}],
        "G003": [{"action_type": "TRANSFER"}],
        "G004": [{"action_type": "PRICING"}],
        "G005": [{"action_type": "REPLENISH"}],  # correctly avoids FRONT_OFFICE
    }
    r = evaluate_classification(GOLDEN_SCENARIOS, outputs)
    assert r["metrics"]["f1"] >= 0.9


def test_classification_forbidden_triggers_fp():
    outputs = {
        "G005": [{"action_type": "FRONT_OFFICE"}],  # chronic returner — forbidden
    }
    r = evaluate_classification(GOLDEN_SCENARIOS, outputs)
    assert r["metrics"]["fp"] >= 1


def test_business_constraints_catch_missing_kpi():
    recs = [
        {"recommendation_id": "R1", "action_type": "FRONT_OFFICE",
         "required_approval": "store_manager", "deadline_hours": 24,
         "success_kpi": ""},
    ]
    r = evaluate_business_constraints(recs)
    assert r["with_violations"] == 1
    assert "missing_success_kpi" in r["details"][0]["violations"]


def test_false_positive_markdown_on_hot_seller():
    recs = [
        {"recommendation_id": "X", "action_type": "MARKDOWN",
         "supporting_metrics": {"weekly_velocity": 25}},
    ]
    fps = detect_false_positives(recs)
    assert fps and fps[0]["false_positive_reason"] == "markdown_on_fast_mover"


def test_run_full_evaluation_produces_summary():
    report = run_full_evaluation(
        agent_outputs={"G001": [{"action_type": "FRONT_OFFICE"}]},
        recommendations=[{
            "recommendation_id": "R", "action_type": "FRONT_OFFICE",
            "required_approval": "store_manager", "deadline_hours": 24,
            "success_kpi": "velocity",
            "supporting_metrics": {},
        }],
        actual_7d=[100, 100, 100],
        forecast_7d=[95, 105, 100],
    )
    assert "summary" in report
    assert report["summary"]["false_positive_count"] == 0
    assert "forecast" in report
