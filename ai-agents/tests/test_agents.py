"""End-to-end + unit tests for the agent system."""
from __future__ import annotations

import pytest

from retail_agents import run_supervisor, RetailDataStore
from retail_agents.data_access import LocalCsvAdapter
from retail_agents.features import inventory_aging_bucket, enrich_inventory
from retail_agents.tools import ToolRegistry
from retail_agents.agents.product_recommendation import ProductRecommendationAgent
from retail_agents.agents.inventory_optimization import InventoryOptimizationAgent
from retail_agents.agents.pricing_optimization import PricingOptimizationAgent
from retail_agents.agents.retail_intelligence import RetailIntelligenceAgent


@pytest.fixture(scope="module")
def tools():
    return ToolRegistry(store=RetailDataStore(adapter=LocalCsvAdapter()))


def test_sample_data_shape(tools):
    products = tools.get_product_catalog()
    assert len(products) == 50
    stores = tools.get_store_catalog()
    assert len(stores) == 5


def test_inventory_bucketing():
    assert inventory_aging_bucket(0)  == "0-30"
    assert inventory_aging_bucket(30) == "0-30"
    assert inventory_aging_bucket(45) == "31-60"
    assert inventory_aging_bucket(90) == "61-90"
    assert inventory_aging_bucket(180) == "91-180"
    assert inventory_aging_bucket(200) == "180+"


def test_enriched_inventory_flags(tools):
    inv = enrich_inventory([dict(r) for r in tools.store.inventory])
    # At least one stockout risk and one excess stock across the dataset
    assert any(r["stockout_risk"] for r in inv)
    assert any(r["excess_stock"] for r in inv)


def test_front_office_produces_ranked_recommendations(tools):
    intel = RetailIntelligenceAgent(tools)
    insights = intel.analyze("S101")
    recs = ProductRecommendationAgent(tools).recommend_front_office("S101", insights, top_n=5)
    assert len(recs) == 5
    scores = [r.supporting_metrics["composite_score"] for r in recs]
    # Monotonic non-increasing
    assert all(a >= b for a, b in zip(scores, scores[1:]))
    # Every rec is grounded
    for r in recs:
        assert r.product_id in {p["product_id"] for p in tools.get_product_catalog()}
        assert len(r.justification) > 40
        assert 0 <= r.confidence <= 1


def test_transfer_recommendations_identify_imbalances(tools):
    intel = RetailIntelligenceAgent(tools)
    insights = intel.analyze("S101")
    recs = InventoryOptimizationAgent(tools)._transfer_recommendations("S101", insights)
    assert len(recs) >= 1
    for r in recs:
        m = r.supporting_metrics
        # Source has >= 12 weeks of cover
        assert m["source_weekly_velocity"] * 12 <= m["source_on_hand"]
        # Destination is stressed: on-hand below 2x reorder point relative to velocity
        destination_weeks_cover = (
            m["destination_on_hand"] / m["destination_weekly_velocity"]
            if m["destination_weekly_velocity"] > 0 else float("inf")
        )
        source_weeks_cover = (
            m["source_on_hand"] / m["source_weekly_velocity"]
            if m["source_weekly_velocity"] > 0 else float("inf")
        )
        assert source_weeks_cover > destination_weeks_cover
        assert m["transfer_quantity"] >= 5


def test_pricing_respects_margin_floor(tools):
    intel = RetailIntelligenceAgent(tools)
    insights = intel.analyze("S101")
    recs = PricingOptimizationAgent(tools).recommend("S101", insights)
    for r in recs:
        m = r.supporting_metrics
        assert m["projected_margin_percent"] >= 10.0


def test_supervisor_end_to_end():
    bundle = run_supervisor("S101")
    assert bundle["store_id"] == "S101"
    assert len(bundle["recommendations"]) > 0
    priorities = {r["priority"] for r in bundle["recommendations"]}
    assert "HIGH" in priorities
    actions = {r["action_type"] for r in bundle["recommendations"]}
    assert "FRONT_OFFICE" in actions
    assert "TRANSFER" in actions or "REPLENISH" in actions
    assert "TARGET" in actions
    for r in bundle["recommendations"]:
        assert r["supporting_metrics"], f"Rec {r['recommendation_id']} missing evidence"
        assert len(r["justification"]) >= 20
