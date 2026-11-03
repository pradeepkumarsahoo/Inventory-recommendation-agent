"""Product Recommendation Agent — front-office placement.

Ranks each (store, product) along a composite retail score. Avoids over-
weighting any single factor; the composition is tunable through weights.
"""
from __future__ import annotations

from ..models import Recommendation
from ..tools import ToolRegistry

WEIGHTS = {
    "velocity": 0.30,
    "margin": 0.25,
    "demand": 0.20,
    "sentiment": 0.15,
    "availability": 0.10,
}


def _normalize(values: list[float]) -> dict[int, float]:
    if not values:
        return {}
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return {i: 0.5 for i in range(len(values))}
    return {i: (v - lo) / (hi - lo) for i, v in enumerate(values)}


class ProductRecommendationAgent:
    name = "ProductRecommendationAgent"

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def recommend_front_office(self, store_id: str, insights: dict, top_n: int = 5) -> list[Recommendation]:
        sales = insights["sales_by_product"]
        inv_by_pid = {r["product_id"]: r for r in insights["inventory"]}
        trends = insights["trends"]
        sentiment = insights["sentiment"]
        returns = insights["returns"]
        products = insights["products"]

        candidates = []
        for key, feats in sales.items():
            _, pid = key.split(":")
            inv = inv_by_pid.get(pid)
            if not inv:
                continue
            on_hand = int(inv["on_hand_quantity"])
            if on_hand < 3:
                continue
            return_rate = returns.get(key, 0.0)
            if return_rate > 0.20:  # exclude chronic returners
                continue
            senti = sentiment.get(key, {}).get("avg_satisfaction", 3.5)
            demand = trends.get(pid, 0.0)
            candidates.append(
                {
                    "pid": pid,
                    "feats": feats,
                    "inv": inv,
                    "demand": demand,
                    "sentiment": senti,
                    "return_rate": return_rate,
                    "product": products.get(pid, {}),
                }
            )

        # Normalize each component across candidates, then score.
        velocity = _normalize([c["feats"]["weekly_velocity"] for c in candidates])
        margin = _normalize([c["feats"]["gross_margin_percent"] for c in candidates])
        demand = _normalize([c["demand"] for c in candidates])
        senti = _normalize([c["sentiment"] for c in candidates])
        avail = _normalize([int(c["inv"]["on_hand_quantity"]) for c in candidates])

        for i, c in enumerate(candidates):
            score = (
                WEIGHTS["velocity"] * velocity[i]
                + WEIGHTS["margin"] * margin[i]
                + WEIGHTS["demand"] * demand[i]
                + WEIGHTS["sentiment"] * senti[i]
                + WEIGHTS["availability"] * avail[i]
            )
            c["score"] = round(score, 4)

        candidates.sort(key=lambda c: c["score"], reverse=True)
        recs: list[Recommendation] = []
        for rank, c in enumerate(candidates[:top_n], start=1):
            feats = c["feats"]
            product = c["product"]
            uplift_units = round(feats["weekly_velocity"] * 0.18, 1)  # 18% front-office uplift assumption
            uplift_revenue = round(uplift_units * float(product.get("base_price", 0)), 2)
            uplift_profit = round(uplift_revenue * feats["gross_margin_percent"] / 100, 2)
            recs.append(
                Recommendation(
                    recommendation_id=f"REC-FO-{store_id}-{c['pid']}",
                    store_id=store_id,
                    product_id=c["pid"],
                    action_type="FRONT_OFFICE",
                    title=f"Feature {product.get('name', c['pid'])} in the front display",
                    justification=(
                        f"Composite retail score {c['score']}: strong velocity "
                        f"({feats['weekly_velocity']}/wk), margin {feats['gross_margin_percent']}%, "
                        f"demand signal {round(c['demand'], 2)}, satisfaction {c['sentiment']}/5."
                    ),
                    supporting_metrics={
                        "composite_score": c["score"],
                        "weekly_velocity": feats["weekly_velocity"],
                        "gross_margin_percent": feats["gross_margin_percent"],
                        "demand_signal": c["demand"],
                        "avg_satisfaction": c["sentiment"],
                        "on_hand_quantity": int(c["inv"]["on_hand_quantity"]),
                        "return_rate": c["return_rate"],
                        "rank": rank,
                    },
                    expected_sales_impact=uplift_revenue,
                    expected_margin_impact=uplift_profit,
                    confidence=min(0.95, 0.55 + c["score"] * 0.35),
                    priority="HIGH" if rank <= 2 else "MEDIUM",
                    risks=[
                        "Uplift assumption is a planning heuristic, not a validated A/B result.",
                        "Trend signal can shift quickly — re-evaluate weekly.",
                    ],
                    assumptions=["18% weekly velocity uplift from front-office placement."],
                    required_approval="store_manager",
                    responsible_role="store_manager",
                    deadline_hours=24,
                    success_kpi="7-day weekly velocity vs pre-placement baseline",
                    source_agent=self.name,
                )
            )
        return recs
