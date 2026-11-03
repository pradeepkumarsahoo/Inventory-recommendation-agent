"""Unit tests for the quantitative inventory optimization engine."""
from __future__ import annotations

import math

import pytest

from retail_agents.optimization import (
    InventoryParameters,
    optimize_sku,
    score_position,
    safety_stock,
    reorder_point,
    economic_order_quantity,
    stockout_probability,
    allocate_proportional,
    apply_supplier_constraints,
    exponential_smoothing_forecast,
)


def test_safety_stock_scales_with_sqrt_of_lead_time():
    s1 = safety_stock(demand_std_daily=3.0, lead_time_days=4, service_level=0.95)
    s2 = safety_stock(demand_std_daily=3.0, lead_time_days=16, service_level=0.95)
    assert pytest.approx(s2 / s1, abs=0.05) == 2.0


def test_reorder_point_includes_safety_buffer():
    rop = reorder_point(demand_mean_daily=5.0, lead_time_days=7, safety=10.0)
    assert rop == 45.0


def test_eoq_basic_formula():
    eoq = economic_order_quantity(
        annual_demand=1200, ordering_cost=50, unit_cost=4.0, holding_cost_rate=0.25
    )
    # sqrt(2 * 1200 * 50 / (4 * 0.25)) = sqrt(120000) ≈ 346
    assert 340 < eoq < 352


def test_stockout_probability_bounds():
    # Deep stock → ~0, zero stock → ~1
    assert stockout_probability(1000, 5.0, 1.0, 7) < 0.01
    assert stockout_probability(0, 5.0, 1.0, 7) > 0.95


def test_optimize_sku_end_to_end():
    daily = [4, 5, 6, 4, 7, 5, 6] * 10
    params = InventoryParameters(
        lead_time_days=5, service_level=0.95, unit_cost=3.0,
        min_order_quantity=10, max_order_quantity=500,
    )
    r = optimize_sku(daily, store_id="S101", sku="P1", params=params)
    assert r.reorder_point > 0
    assert r.safety_stock > 0
    assert r.economic_order_qty >= 10
    assert r.service_level_used == 0.95


def test_score_position_actions():
    daily = [10] * 30
    params = InventoryParameters(lead_time_days=5, service_level=0.95, unit_cost=2.0)
    r = optimize_sku(daily, "S1", "P", params)
    low = score_position(r, on_hand=1, params=params)
    high = score_position(r, on_hand=1000, params=params)
    assert low["recommended_action"] in ("REORDER", "EXPEDITE")
    assert high["recommended_action"] in ("HOLD_OR_TRANSFER_OUT", "HOLD")


def test_allocate_proportional_sum_matches_available():
    alloc = allocate_proportional(100, {"S1": 10.0, "S2": 20.0, "S3": 30.0})
    assert sum(alloc.values()) == 100


def test_allocate_proportional_handles_zero_demand():
    alloc = allocate_proportional(50, {"S1": 0, "S2": 0})
    assert alloc == {"S1": 0, "S2": 0}


def test_supplier_constraints_clamp():
    params = InventoryParameters(min_order_quantity=10, max_order_quantity=100)
    assert apply_supplier_constraints(5, params) == 10
    assert apply_supplier_constraints(150, params) == 100
    assert apply_supplier_constraints(50, params) == 50


def test_exponential_smoothing_tracks_trend():
    assert exponential_smoothing_forecast([5, 5, 5, 5]) == 5.0
    f = exponential_smoothing_forecast([1, 2, 3, 4, 5], alpha=0.5)
    assert 3.0 < f < 5.0
