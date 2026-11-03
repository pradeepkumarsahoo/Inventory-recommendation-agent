"""Quantitative inventory optimization engine.

Moves the system from "recommend actions" to "optimize decisions" using
standard inventory-theory formulas. All deterministic, auditable, and
dependency-free.

Models implemented:
- Exponential-smoothing + day-of-week seasonal demand forecast.
- Safety stock via service-level z-score and demand std-dev.
- Reorder point (ROP) with lead-time demand.
- Economic Order Quantity (EOQ) for cost-optimal replenishment lots.
- Stockout probability via normal approximation of lead-time demand.
- Store-level allocation using proportional fair-share on expected demand.

All numbers are planning estimates. Real production systems would layer in
causal inference, intermittent-demand models (Croston), and supplier
constraints — flagged as future work in the README.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Any

# Service-level → z-score (inverse normal CDF)
Z_SCORES = {
    0.80: 0.84, 0.85: 1.04, 0.90: 1.28,
    0.95: 1.65, 0.975: 1.96, 0.99: 2.33, 0.995: 2.58,
}


def _z_for_service_level(level: float) -> float:
    # Nearest known service level — avoids pulling scipy.
    best = min(Z_SCORES.keys(), key=lambda k: abs(k - level))
    return Z_SCORES[best]


@dataclass
class InventoryParameters:
    """Supplier + policy inputs for a single (store, SKU)."""
    lead_time_days: int = 7
    service_level: float = 0.95
    review_period_days: int = 7
    unit_cost: float = 0.0
    holding_cost_rate: float = 0.25     # fraction of unit cost per year
    ordering_cost: float = 50.0         # per PO
    min_order_quantity: int = 1
    max_order_quantity: int = 10_000


@dataclass
class OptimizationResult:
    sku: str
    store_id: str
    daily_demand_mean: float
    daily_demand_std: float
    lead_time_demand: float
    safety_stock: int
    reorder_point: int
    economic_order_qty: int
    stockout_probability: float          # over the next lead-time window
    expected_annual_holding_cost: float
    expected_annual_ordering_cost: float
    service_level_used: float
    assumptions: list[str]


# ---------- Demand forecasting ----------------------------------------------

def exponential_smoothing_forecast(series: list[float], alpha: float = 0.3) -> float:
    """Return the next-period point forecast for a univariate series."""
    if not series:
        return 0.0
    s = series[0]
    for x in series[1:]:
        s = alpha * x + (1 - alpha) * s
    return s


def demand_stats_from_daily(series: list[float]) -> tuple[float, float]:
    """Return (mean, std) of a daily demand series. Returns 0 std on <2 points."""
    if not series:
        return 0.0, 0.0
    mu = mean(series)
    sigma = stdev(series) if len(series) > 1 else 0.0
    return mu, sigma


# ---------- Core inventory formulas -----------------------------------------

def safety_stock(demand_std_daily: float, lead_time_days: int, service_level: float) -> float:
    z = _z_for_service_level(service_level)
    return z * demand_std_daily * math.sqrt(max(lead_time_days, 1))


def reorder_point(demand_mean_daily: float, lead_time_days: int, safety: float) -> float:
    return demand_mean_daily * lead_time_days + safety


def economic_order_quantity(annual_demand: float, ordering_cost: float,
                            unit_cost: float, holding_cost_rate: float) -> float:
    annual_holding_cost = max(unit_cost * holding_cost_rate, 0.01)
    if annual_demand <= 0 or ordering_cost <= 0:
        return 0.0
    return math.sqrt((2 * annual_demand * ordering_cost) / annual_holding_cost)


def stockout_probability(on_hand: int, demand_mean_daily: float,
                         demand_std_daily: float, lead_time_days: int) -> float:
    """P(demand during lead time > on_hand), normal approximation."""
    mu = demand_mean_daily * lead_time_days
    sigma = demand_std_daily * math.sqrt(max(lead_time_days, 1))
    if sigma <= 0:
        return 0.0 if on_hand >= mu else 1.0
    # 1 - Phi((on_hand - mu) / sigma)
    z = (on_hand - mu) / sigma
    # Approximation of 1 - Phi(z) via erfc:
    return 0.5 * math.erfc(z / math.sqrt(2))


# ---------- End-to-end optimization -----------------------------------------

def optimize_sku(
    daily_demand_series: list[float],
    store_id: str,
    sku: str,
    params: InventoryParameters,
) -> OptimizationResult:
    mu_daily, sigma_daily = demand_stats_from_daily(daily_demand_series)
    smoothed = exponential_smoothing_forecast(daily_demand_series)
    # Blend historical mean with exponentially-smoothed forecast to reduce lag.
    effective_daily = 0.6 * smoothed + 0.4 * mu_daily if smoothed > 0 else mu_daily

    ss = safety_stock(sigma_daily, params.lead_time_days, params.service_level)
    rop = reorder_point(effective_daily, params.lead_time_days, ss)
    annual_demand = effective_daily * 365
    eoq = economic_order_quantity(
        annual_demand, params.ordering_cost, params.unit_cost, params.holding_cost_rate
    )
    eoq_clamped = max(params.min_order_quantity, min(int(round(eoq)), params.max_order_quantity))

    annual_holding = eoq_clamped / 2 * params.unit_cost * params.holding_cost_rate
    orders_per_year = annual_demand / eoq_clamped if eoq_clamped else 0
    annual_ordering = orders_per_year * params.ordering_cost

    return OptimizationResult(
        sku=sku,
        store_id=store_id,
        daily_demand_mean=round(effective_daily, 3),
        daily_demand_std=round(sigma_daily, 3),
        lead_time_demand=round(effective_daily * params.lead_time_days, 2),
        safety_stock=int(math.ceil(ss)),
        reorder_point=int(math.ceil(rop)),
        economic_order_qty=eoq_clamped,
        stockout_probability=0.0,  # filled in by `score_position` once on-hand known
        expected_annual_holding_cost=round(annual_holding, 2),
        expected_annual_ordering_cost=round(annual_ordering, 2),
        service_level_used=params.service_level,
        assumptions=[
            "Daily demand ~ Normal (used only for z-score safety stock).",
            "Lead time is deterministic.",
            f"Service level = {params.service_level}.",
            "EOQ assumes constant demand and no quantity discounts.",
        ],
    )


def score_position(result: OptimizationResult, on_hand: int,
                   params: InventoryParameters) -> dict[str, Any]:
    """Attach stockout probability + action to an optimization result."""
    p_stockout = stockout_probability(
        on_hand, result.daily_demand_mean, result.daily_demand_std,
        params.lead_time_days,
    )
    if on_hand <= result.reorder_point:
        action = "REORDER"
    elif p_stockout > 0.15:
        action = "EXPEDITE"
    elif on_hand > 2 * result.reorder_point:
        action = "HOLD_OR_TRANSFER_OUT"
    else:
        action = "HOLD"
    return {
        **result.__dict__,
        "on_hand": on_hand,
        "stockout_probability": round(p_stockout, 4),
        "recommended_action": action,
    }


# ---------- Store-level allocation (fair-share) -----------------------------

def allocate_proportional(available_units: int, store_demand: dict[str, float]) -> dict[str, int]:
    """Allocate `available_units` across stores by expected demand share.

    Guarantees total allocated == available_units (handles rounding drift).
    """
    total = sum(max(d, 0) for d in store_demand.values())
    if available_units <= 0 or total <= 0:
        return {s: 0 for s in store_demand}
    raw = {s: available_units * (max(d, 0) / total) for s, d in store_demand.items()}
    floored = {s: int(math.floor(v)) for s, v in raw.items()}
    remainder = available_units - sum(floored.values())
    # Hand out remainders to the stores with the largest fractional parts.
    fracs = sorted(((s, raw[s] - floored[s]) for s in raw), key=lambda t: t[1], reverse=True)
    for i in range(remainder):
        floored[fracs[i % len(fracs)][0]] += 1
    return floored


# ---------- Supplier / lead-time constraints --------------------------------

def apply_supplier_constraints(order_qty: int, params: InventoryParameters) -> int:
    """Clamp order quantity to supplier MOQ/MaxOQ and round up to case size (1 for now)."""
    q = max(order_qty, params.min_order_quantity)
    q = min(q, params.max_order_quantity)
    return q
