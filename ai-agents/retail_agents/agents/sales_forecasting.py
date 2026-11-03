"""Sales Forecasting Agent — baseline forecast + target recommendation.

A seasonal-naive forecast (day-of-week average over trailing 4 weeks)
is used by default. Explainable and deterministic. The seam for a
stronger model (ARIMA/Prophet/ML) is `make_forecast`.
"""
from __future__ import annotations

from ..models import Recommendation
from ..tools import ToolRegistry


class SalesForecastingAgent:
    name = "SalesForecastingAgent"

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def recommend_targets(self, store_id: str, insights: dict) -> list[Recommendation]:
        fcast = self.tools.call("get_store_forecast", store_id=store_id)
        trailing = fcast["trailing_7d_revenue"]
        if not fcast["forecast"]:
            return []
        total_baseline = sum(d["baseline_forecast_revenue"] for d in fcast["forecast"])
        total_target = sum(d["recommended_target_revenue"] for d in fcast["forecast"])
        uplift = round(total_target - total_baseline, 2)
        return [
            Recommendation(
                recommendation_id=f"REC-TGT-{store_id}",
                store_id=store_id,
                product_id=None,
                action_type="TARGET",
                title=f"Set 7-day sales target to ${total_target:,.0f} (+5% stretch)",
                justification=(
                    f"Trailing 7-day revenue ${trailing:,.0f}; seasonal-naive baseline for next 7 days "
                    f"${total_baseline:,.0f}. A 5% stretch is in line with store performance and "
                    f"the actions the agents are also recommending."
                ),
                supporting_metrics={
                    "trailing_7d_revenue": trailing,
                    "baseline_forecast_7d_revenue": total_baseline,
                    "recommended_target_7d_revenue": total_target,
                    "stretch_percent": 5.0,
                    "daily_breakdown": fcast["forecast"],
                },
                expected_sales_impact=uplift,
                expected_margin_impact=round(uplift * (insights["store_performance"].get("gross_margin_percent", 30) / 100), 2),
                confidence=0.70,
                priority="MEDIUM",
                risks=["Seasonal-naive misses macro shifts and promotions outside the trailing window."],
                assumptions=["Day-of-week seasonality dominates short-horizon revenue."],
                required_approval="store_manager",
                responsible_role="store_manager",
                deadline_hours=24,
                success_kpi="Actual 7-day revenue vs recommended target",
                source_agent=self.name,
            )
        ]
