"""End-to-end integration test exercising the whole stack via Python.

This test drives the supervisor + guardrails + report generator in one pass.
It is the integration equivalent of what the C# API's /api/agent/analyze
endpoint does for a store.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-agents"))
sys.path.insert(0, str(ROOT / "ai-guardrails" / "service"))

from retail_agents import run_supervisor  # noqa: E402
from guardrail_service import GuardrailService  # noqa: E402


def test_supervisor_output_passes_guardrail_validation():
    bundle = run_supervisor("S101")
    svc = GuardrailService()
    for rec in bundle["recommendations"]:
        verdict = svc.validate_recommendation(rec)
        assert verdict["allowed"], f"Rejected: {rec['recommendation_id']}: {verdict['reason']}"


def test_report_generation_runs_without_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    import importlib
    gen = importlib.import_module("reports.generate_report")
    bundle = run_supervisor("S102")
    html = gen.build_html(bundle)
    assert "Daily Store Decision Report" in html
    assert "S102" in html
    # Report embeds at least a few action cards
    assert html.count("action-card") >= 3


def test_all_stores_produce_recommendations():
    for s in ("S101", "S102", "S103", "S104", "S105"):
        bundle = run_supervisor(s)
        assert bundle["recommendations"], f"No recs for {s}"


def test_bundle_is_json_serializable():
    bundle = run_supervisor("S101")
    json.dumps(bundle, default=str)  # must not raise
