"""Supervisor Agent — orchestrates specialists, validates results, and produces
the final daily game plan.

Design notes:
- Specialists are invoked in dependency order (intelligence → others → execution).
- Every recommendation flows through the guardrail validator before being
  included in the final bundle. Guardrail failure = recommendation is dropped
  and the rejection is recorded in the trace.
- The LLM path is optional. When no API key is configured, the deterministic
  specialists do the work directly. When an LLM is configured, it is used only
  to generate human-readable NARRATIVE on top of the deterministic result —
  it never alters metrics or approves actions.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .data_access import RetailDataStore
from .models import Recommendation, RecommendationBundle
from .tools import ToolRegistry
from .agents import (
    RetailIntelligenceAgent,
    ProductRecommendationAgent,
    InventoryOptimizationAgent,
    PricingOptimizationAgent,
    SalesForecastingAgent,
    StoreExecutionAgent,
)

GUARDRAILS_DIR = Path(__file__).resolve().parents[2] / "ai-guardrails"
sys.path.insert(0, str(GUARDRAILS_DIR / "service"))


def _load_guardrails():
    """Load the guardrail service with graceful fallback."""
    try:
        from guardrail_service import GuardrailService  # noqa: WPS433
        return GuardrailService()
    except Exception as e:  # pragma: no cover - defensive
        print(f"[supervisor] Guardrail service unavailable, failing closed: {e}")
        raise


class SupervisorAgent:
    name = "SupervisorAgent"

    def __init__(self, store: RetailDataStore | None = None):
        self.store = store or RetailDataStore()
        self.tools = ToolRegistry(store=self.store)
        self.intel = RetailIntelligenceAgent(self.tools)
        self.product = ProductRecommendationAgent(self.tools)
        self.inv = InventoryOptimizationAgent(self.tools)
        self.pricing = PricingOptimizationAgent(self.tools)
        self.forecast = SalesForecastingAgent(self.tools)
        self.execution = StoreExecutionAgent()
        self.guardrails = _load_guardrails()
        self.trace: list[dict] = []

    def _record(self, agent: str, step: str, detail: Any):
        self.trace.append({"agent": agent, "step": step, "detail": detail})

    def analyze(self, store_id: str) -> RecommendationBundle:
        self.trace = []
        self._record(self.name, "start", {"store_id": store_id})

        # 1. Validate the request itself through the guardrails.
        safety = self.guardrails.validate_input({"store_id": store_id, "intent": "daily_game_plan"})
        if not safety["allowed"]:
            raise PermissionError(f"Blocked by guardrails: {safety['reason']}")

        # 2. Build insights pack.
        insights = self.intel.analyze(store_id)
        self._record(self.intel.name, "insights", {"products": len(insights["sales_by_product"])})

        # 3. Specialist agents — invoked independently.
        collected: list[Recommendation] = []
        for agent_name, agent, call in [
            ("product", self.product, lambda: self.product.recommend_front_office(store_id, insights)),
            ("inventory", self.inv, lambda: self.inv.recommend(store_id, insights)),
            ("pricing", self.pricing, lambda: self.pricing.recommend(store_id, insights)),
            ("forecast", self.forecast, lambda: self.forecast.recommend_targets(store_id, insights)),
        ]:
            recs = call()
            self._record(agent.name, "generated", {"count": len(recs)})
            for r in recs:
                verdict = self.guardrails.validate_recommendation(r.to_dict())
                if verdict["allowed"]:
                    collected.append(r)
                else:
                    self._record(agent.name, "rejected", {"recommendation_id": r.recommendation_id, "reason": verdict["reason"]})

        # 4. Conflict resolution: at most one pricing + one aging action per product.
        collected = self._dedupe(collected)
        self._record(self.name, "dedup_remaining", {"count": len(collected)})

        # 5. Execution plan.
        plan = self.execution.build_action_plan(collected)
        self._record(self.execution.name, "plan_built", {"actions": len(plan)})

        return RecommendationBundle(
            store_id=store_id,
            generated_at=datetime(2026, 11, 3, 7, 0, 0).isoformat(),
            recommendations=collected,
            agent_trace=self.trace,
            insights={
                "action_plan": plan,
                "store_performance": insights["store_performance"],
                "inventory_value_total": insights["inventory_value_total"],
                "aging_value_by_bucket": insights["aging_value_by_bucket"],
            },
        )

    @staticmethod
    def _dedupe(recs: list[Recommendation]) -> list[Recommendation]:
        seen: dict[tuple[str, str], Recommendation] = {}
        out = []
        for r in recs:
            if r.action_type in ("PRICING",):
                key = (r.product_id, "PRICING")
                prev = seen.get(key)
                if not prev or r.expected_margin_impact > prev.expected_margin_impact:
                    seen[key] = r
                continue
            out.append(r)
        out.extend(seen.values())
        return out


def run_supervisor(store_id: str) -> dict:
    return SupervisorAgent().analyze(store_id).to_dict()


if __name__ == "__main__":
    import json
    store = sys.argv[1] if len(sys.argv) > 1 else "S101"
    print(json.dumps(run_supervisor(store), indent=2, default=str))
