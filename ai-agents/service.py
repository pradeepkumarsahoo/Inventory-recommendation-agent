"""FastAPI service exposing the retail agent system over HTTP.

This is the one well-defined contract between the .NET API and the Python
agent code. The .NET API no longer shells into python3 per request; it
calls these endpoints. That gives us connection pooling, observability
hooks, and a single serialization boundary.

Endpoints:
    GET  /health
    POST /recommendations/{store_id}           → run deterministic supervisor
    POST /recommendations/{store_id}/intelligent → structured-output agent
    POST /recommendations/{store_id}/langchain   → LangChain supervisor (optional)
    POST /simulation/{store_id}                → baseline-vs-AI impact simulation
    POST /evaluation                           → run golden-dataset evaluation
    GET  /metrics                              → observability snapshot
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:
    raise SystemExit(
        "FastAPI is required for the agents service. "
        f"Install with: pip install fastapi uvicorn. ({e})"
    )

# Make sibling retail_agents package importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retail_agents import run_supervisor, RetailDataStore  # noqa: E402
from retail_agents.intelligent_agent import IntelligentRetailAgent  # noqa: E402
from retail_agents.simulation import compare, SKUState  # noqa: E402
from retail_agents.evaluation import run_full_evaluation  # noqa: E402
from retail_agents.observability import METRICS  # noqa: E402
from retail_agents.explainability import explain_all  # noqa: E402

app = FastAPI(title="Retail Agents Service", version="1.0.0")

_store = RetailDataStore()


class IntentRequest(BaseModel):
    intent: str = "daily_game_plan"
    prompt: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "data_loaded": bool(_store.products)}


@app.post("/recommendations/{store_id}")
def recommendations(store_id: str, body: IntentRequest = IntentRequest()) -> dict:
    try:
        bundle = run_supervisor(store_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    bundle["recommendations"] = explain_all(bundle["recommendations"])
    return bundle


@app.post("/recommendations/{store_id}/intelligent")
def intelligent(store_id: str, body: IntentRequest = IntentRequest()) -> dict:
    agent = IntelligentRetailAgent(store=_store)
    out = agent.run(store_id, user_prompt=body.prompt or body.intent)
    out["recommendations"] = explain_all(out["recommendations"])
    return out


@app.post("/recommendations/{store_id}/langchain")
def langchain(store_id: str) -> dict:
    try:
        from retail_agents.langchain_supervisor import LangChainSupervisor
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LangChain unavailable: {e}")
    try:
        return LangChainSupervisor(store=_store).analyze(store_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SimulationRequest(BaseModel):
    recommendations: list[dict]


@app.post("/simulation/{store_id}")
def simulation(store_id: str, body: SimulationRequest) -> dict:
    inv = [r for r in _store.inventory if r["store_id"] == store_id]
    products_by_id = {p["product_id"]: p for p in _store.products}
    skus = []
    for row in inv:
        pid = row["product_id"]
        p = products_by_id.get(pid, {})
        skus.append(SKUState(
            product_id=pid,
            on_hand=int(row["on_hand_quantity"]),
            weekly_velocity=float(row.get("weekly_sales_velocity", 0.0)),
            base_price=float(p.get("base_price", 0.0)),
            unit_cost=float(p.get("cost", 0.0)),
            age_days=int(row.get("age_days", 0)),
            aging_bucket=str(row.get("aging_bucket", "")),
        ))
    return compare(skus, body.recommendations)


class EvaluationRequest(BaseModel):
    agent_outputs: dict[str, list[dict]] = {}
    recommendations: list[dict] = []
    actual_7d: list[float] | None = None
    forecast_7d: list[float] | None = None


@app.post("/evaluation")
def evaluation(body: EvaluationRequest) -> dict:
    return run_full_evaluation(
        agent_outputs=body.agent_outputs,
        recommendations=body.recommendations,
        actual_7d=body.actual_7d,
        forecast_7d=body.forecast_7d,
    )


@app.get("/metrics")
def metrics() -> dict:
    return METRICS.snapshot()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    port = int(os.environ.get("PORT", "7071"))
    uvicorn.run(app, host="0.0.0.0", port=port)
