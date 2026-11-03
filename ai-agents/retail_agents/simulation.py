"""Business-impact simulation: baseline vs AI-recommended decisions.

Produces a side-by-side 7-day P&L comparison between (a) the store's
current / baseline inventory policy and (b) the AI-recommended policy.

All results are SIMULATED, not actual business outcomes. Elasticity,
uplift, and shrink coefficients are planning heuristics documented
alongside each metric so a reader can judge sensitivity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------- Default planning assumptions ------------------------------------
# These are the tunable knobs. Each one is documented in-line because any
# claim about "AI improves revenue by X%" rests on these numbers.

ASSUMPTIONS = {
    "front_office_uplift_pct": 0.18,       # +18% weekly velocity on featured SKUs
    "markdown_sell_through_pct": 0.65,     # % of aged units cleared via markdown in 30d
    "markdown_margin_hit_pct": 0.15,       # 15 pp margin erosion on marked-down units
    "transfer_execution_rate": 0.85,       # 85% of recommended transfers executed in-week
    "pricing_elasticity": -1.1,            # 1% price down → +1.1% units
    "carrying_cost_rate_annual": 0.25,     # 25% of unit cost / year
    "stockout_margin_lost_pct": 0.80,      # 80% of margin lost per stockout day
}


@dataclass
class SKUState:
    product_id: str
    on_hand: int
    weekly_velocity: float
    base_price: float
    unit_cost: float
    age_days: int
    aging_bucket: str

    @property
    def margin_per_unit(self) -> float:
        return max(self.base_price - self.unit_cost, 0.0)

    @property
    def margin_pct(self) -> float:
        return (self.margin_per_unit / self.base_price) if self.base_price else 0.0


@dataclass
class WeeklyPnL:
    revenue: float
    gross_profit: float
    units_sold: int
    stockouts: int
    aged_units_remaining: int
    carrying_cost: float

    def to_dict(self) -> dict:
        return {
            "revenue": round(self.revenue, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_margin_pct": round(self.gross_profit / self.revenue * 100, 2)
            if self.revenue else 0.0,
            "units_sold": self.units_sold,
            "stockouts": self.stockouts,
            "aged_units_remaining": self.aged_units_remaining,
            "carrying_cost": round(self.carrying_cost, 2),
            "net_profit": round(self.gross_profit - self.carrying_cost, 2),
        }


# ---------- Baseline policy -------------------------------------------------

def simulate_baseline_week(skus: list[SKUState]) -> WeeklyPnL:
    """What happens if we do nothing: velocity continues, aged inventory lingers."""
    revenue = profit = carrying_cost = 0.0
    units = stockouts = aged = 0
    for s in skus:
        demand_this_week = s.weekly_velocity
        sold = min(demand_this_week, s.on_hand)
        revenue += sold * s.base_price
        profit += sold * s.margin_per_unit
        units += int(round(sold))
        if s.on_hand < demand_this_week:
            stockouts += 1
            # Lost margin on missed demand
            profit -= (demand_this_week - s.on_hand) * s.margin_per_unit * \
                ASSUMPTIONS["stockout_margin_lost_pct"]
        if s.age_days >= 90:
            aged += s.on_hand - int(round(sold))
        # 1-week share of annual carrying cost on leftover stock
        leftover = max(s.on_hand - sold, 0)
        carrying_cost += leftover * s.unit_cost * ASSUMPTIONS["carrying_cost_rate_annual"] / 52
    return WeeklyPnL(revenue, profit, units, stockouts, aged, carrying_cost)


# ---------- AI-recommended policy -------------------------------------------

def simulate_ai_week(skus: list[SKUState], recommendations: list[dict]) -> WeeklyPnL:
    """What happens if we execute the AI recommendations.

    Applies the planning heuristics in ASSUMPTIONS to each recommendation
    type. Metrics are additive on top of the baseline per-SKU calculation.
    """
    rec_by_product: dict[str, list[dict]] = {}
    for r in recommendations:
        pid = r.get("product_id")
        if pid:
            rec_by_product.setdefault(pid, []).append(r)

    revenue = profit = carrying_cost = 0.0
    units = stockouts = aged = 0

    for s in skus:
        actions = [r.get("action_type") for r in rec_by_product.get(s.product_id, [])]

        velocity = s.weekly_velocity
        margin = s.margin_per_unit
        price = s.base_price
        on_hand_effective = s.on_hand

        # Front-office uplift
        if "FRONT_OFFICE" in actions:
            velocity *= (1 + ASSUMPTIONS["front_office_uplift_pct"])

        # Pricing-down: elastic uplift, margin hit
        if "PRICING" in actions:
            price_drop_pct = 0.05
            velocity *= (1 + price_drop_pct * abs(ASSUMPTIONS["pricing_elasticity"]))
            margin -= price * price_drop_pct

        # Markdown clearance on aged stock
        if "MARKDOWN" in actions and s.age_days >= 90:
            cleared = int(round(s.on_hand * ASSUMPTIONS["markdown_sell_through_pct"]))
            cleared_margin = (margin - price * ASSUMPTIONS["markdown_margin_hit_pct"])
            revenue += cleared * price * (1 - ASSUMPTIONS["markdown_margin_hit_pct"])
            profit += cleared * max(cleared_margin, 0)
            on_hand_effective -= cleared

        # Transfer in — assume 85% execution of a logical top-up to 2 weeks of cover
        if "TRANSFER" in actions and on_hand_effective < 2 * velocity:
            top_up = int(round(2 * velocity - on_hand_effective))
            on_hand_effective += int(top_up * ASSUMPTIONS["transfer_execution_rate"])

        # Normal week-on sales under new policy
        sold = min(velocity, on_hand_effective)
        revenue += sold * price
        profit += sold * max(margin, 0)
        units += int(round(sold))
        if on_hand_effective < velocity:
            stockouts += 1
            profit -= (velocity - on_hand_effective) * max(margin, 0) * \
                ASSUMPTIONS["stockout_margin_lost_pct"]
        leftover = max(on_hand_effective - sold, 0)
        if s.age_days >= 90 and "MARKDOWN" not in actions:
            aged += leftover
        carrying_cost += leftover * s.unit_cost * ASSUMPTIONS["carrying_cost_rate_annual"] / 52

    return WeeklyPnL(revenue, profit, units, stockouts, aged, carrying_cost)


# ---------- Reporting -------------------------------------------------------

def compare(skus: list[SKUState], recommendations: list[dict]) -> dict[str, Any]:
    base = simulate_baseline_week(skus)
    ai = simulate_ai_week(skus, recommendations)
    base_d, ai_d = base.to_dict(), ai.to_dict()
    deltas = {
        "revenue_delta": round(ai_d["revenue"] - base_d["revenue"], 2),
        "revenue_delta_pct": round(_pct(ai_d["revenue"], base_d["revenue"]), 2),
        "gross_profit_delta": round(ai_d["gross_profit"] - base_d["gross_profit"], 2),
        "gross_profit_delta_pct": round(_pct(ai_d["gross_profit"], base_d["gross_profit"]), 2),
        "gross_margin_pp_delta": round(ai_d["gross_margin_pct"] - base_d["gross_margin_pct"], 2),
        "stockouts_delta": ai_d["stockouts"] - base_d["stockouts"],
        "aged_units_delta": ai_d["aged_units_remaining"] - base_d["aged_units_remaining"],
        "carrying_cost_delta": round(ai_d["carrying_cost"] - base_d["carrying_cost"], 2),
        "net_profit_delta": round(ai_d["net_profit"] - base_d["net_profit"], 2),
        "sell_through_improvement_pct": round(
            _pct(ai_d["units_sold"], base_d["units_sold"]), 2),
    }
    return {
        "baseline": base_d,
        "ai": ai_d,
        "deltas": deltas,
        "assumptions": ASSUMPTIONS,
        "disclaimer": (
            "SIMULATED RESULTS. Elasticity, uplift, and sell-through rates are "
            "planning heuristics, not validated outcomes. Treat as directional, "
            "not predictive. See `assumptions` for every coefficient used."
        ),
    }


def _pct(a: float, b: float) -> float:
    return ((a - b) / b * 100) if b else 0.0
