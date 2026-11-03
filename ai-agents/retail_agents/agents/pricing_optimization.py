"""Pricing Optimization Agent.

Pricing is sensitive, so the agent is conservative:
- Never recommends a price below cost + minimum margin floor.
- Flags assumptions clearly (demand elasticity is a planning heuristic,
  not a validated model).
- Avoids claiming "optimal" prices; recommends ranges and expected
  outcomes.
"""
from __future__ import annotations

from ..models import Recommendation
from ..tools import ToolRegistry

MIN_MARGIN_FLOOR = 0.10  # never drop margin below 10%
ELASTICITY_ASSUMPTION = -1.3  # 1% price cut -> ~1.3% volume uplift (planning heuristic)


class PricingOptimizationAgent:
    name = "PricingOptimizationAgent"

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def recommend(self, store_id: str, insights: dict) -> list[Recommendation]:
        recs: list[Recommendation] = []
        products = insights["products"]
        sales = insights["sales_by_product"]
        inv_by_pid = {r["product_id"]: r for r in insights["inventory"]}
        returns = insights["returns"]

        for key, feats in sales.items():
            _, pid = key.split(":")
            product = products.get(pid)
            if not product:
                continue
            inv = inv_by_pid.get(pid)
            if not inv:
                continue
            on_hand = int(inv["on_hand_quantity"])
            velocity = feats["weekly_velocity"]
            margin_pct = feats["gross_margin_percent"] / 100
            return_rate = returns.get(key, 0.0)

            price_change = _decide_price_direction(feats, inv, return_rate)
            if not price_change:
                continue
            direction, pct, rationale = price_change
            current_price = float(product["base_price"])
            new_price = round(current_price * (1 + pct / 100), 2)
            new_margin = _margin_at_price(new_price, float(product["cost"]))
            if new_margin < MIN_MARGIN_FLOOR:
                continue  # skip — would violate margin floor

            vol_change = ELASTICITY_ASSUMPTION * pct / 100  # relative change
            projected_weekly_units = max(0.0, velocity * (1 + vol_change))
            delta_revenue = round((projected_weekly_units * new_price) - (velocity * current_price), 2)
            delta_profit = round(
                (projected_weekly_units * (new_price - float(product["cost"])))
                - (velocity * (current_price - float(product["cost"]))),
                2,
            )
            recs.append(
                Recommendation(
                    recommendation_id=f"REC-PRICE-{store_id}-{pid}",
                    store_id=store_id,
                    product_id=pid,
                    action_type="PRICING",
                    title=f"{direction} price on {product['name']} by {abs(pct)}%",
                    justification=rationale,
                    supporting_metrics={
                        "current_price": current_price,
                        "proposed_price_range": [round(min(current_price, new_price), 2), round(max(current_price, new_price), 2)],
                        "cost": float(product["cost"]),
                        "current_margin_percent": round(margin_pct * 100, 2),
                        "projected_margin_percent": round(new_margin * 100, 2),
                        "weekly_velocity": velocity,
                        "on_hand_quantity": on_hand,
                        "return_rate": return_rate,
                        "price_change_percent": pct,
                        "elasticity_assumption": ELASTICITY_ASSUMPTION,
                    },
                    expected_sales_impact=delta_revenue,
                    expected_margin_impact=delta_profit,
                    confidence=0.60,
                    priority="MEDIUM" if abs(pct) <= 5 else "HIGH",
                    risks=[
                        "Elasticity is an assumption, not a measured value.",
                        "Competitor response can offset the projected volume change.",
                    ],
                    assumptions=[
                        f"Short-run elasticity ≈ {ELASTICITY_ASSUMPTION}.",
                        f"Minimum gross margin floor {int(MIN_MARGIN_FLOOR*100)}%.",
                    ],
                    required_approval="regional_manager",
                    responsible_role="pricing_manager",
                    deadline_hours=48,
                    success_kpi="Realized gross profit vs projection over 14 days",
                    source_agent=self.name,
                )
            )
        return recs


def _decide_price_direction(feats, inv, return_rate) -> tuple[str, float, str] | None:
    """Returns (direction, pct_change, rationale) or None."""
    velocity = feats["weekly_velocity"]
    margin_pct = feats["gross_margin_percent"] / 100
    on_hand = int(inv["on_hand_quantity"])
    weeks_cover = (on_hand / velocity) if velocity > 0 else float("inf")

    # Case A: slow mover with excess cover and healthy margin — small cut
    if velocity > 0 and weeks_cover > 10 and margin_pct > 0.35 and return_rate < 0.15:
        return (
            "Decrease",
            -5.0,
            f"Weeks of cover {round(weeks_cover,1)} on margin {round(margin_pct*100,1)}% — a 5% cut can accelerate sell-through "
            f"while staying above the 10% margin floor.",
        )
    # Case B: fast mover with low cover and premium margin — modest increase
    if velocity > 0 and weeks_cover < 2 and margin_pct > 0.45 and return_rate < 0.08:
        return (
            "Increase",
            3.0,
            f"Weeks of cover {round(weeks_cover,1)} with margin {round(margin_pct*100,1)}% and low returns — "
            f"a 3% increase likely holds demand while improving profit per unit.",
        )
    # Case C: high returns — do not reduce price; flag no change
    if return_rate > 0.2:
        return None  # pricing is not the lever here
    return None


def _margin_at_price(price: float, cost: float) -> float:
    return (price - cost) / price if price > 0 else 0.0
