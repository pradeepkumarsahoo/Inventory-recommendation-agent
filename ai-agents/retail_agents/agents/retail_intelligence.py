"""Retail Intelligence Agent — synthesizes insight across all datasets.

Does not emit recommendations directly; it builds the shared evidence
pack the specialist agents consume. Keeping this separate avoids each
specialist re-aggregating the same features.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from ..tools import ToolRegistry


class RetailIntelligenceAgent:
    name = "RetailIntelligenceAgent"

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def analyze(self, store_id: str) -> dict[str, Any]:
        sales = self.tools.call("get_sales_summary")  # keyed by "store:product"
        inv = self.tools.call("get_inventory_position")
        returns = self.tools.call("get_return_rates")
        sentiment = self.tools.call("get_survey_sentiment")
        trends = self.tools.call("get_trending_products")
        products = {p["product_id"]: p for p in self.tools.call("get_product_catalog")}

        # per-product company-wide velocity (across all stores)
        total_units_by_product: dict[str, int] = defaultdict(int)
        total_revenue_by_product: dict[str, float] = defaultdict(float)
        for key, v in sales.items():
            _, pid = key.split(":")
            total_units_by_product[pid] += v["units_sold"]
            total_revenue_by_product[pid] += v["revenue"]

        store_sales = {k: v for k, v in sales.items() if k.startswith(store_id + ":")}
        store_inv = [r for r in inv if r["store_id"] == store_id]

        aging_value = defaultdict(float)
        for r in store_inv:
            p = products.get(r["product_id"], {})
            value = int(r["on_hand_quantity"]) * float(p.get("cost", 0))
            aging_value[r["aging_bucket"]] += value

        total_inv_value = sum(aging_value.values())
        store_perf = next((s for s in self.tools.store.store_performance if s["store_id"] == store_id), {})

        return {
            "store_id": store_id,
            "sales_by_product": store_sales,
            "inventory": store_inv,
            "returns": {k: v for k, v in returns.items() if k.startswith(store_id + ":")},
            "sentiment": {k: v for k, v in sentiment.items() if k.startswith(store_id + ":")},
            "trends": trends,
            "products": products,
            "company_units_by_product": total_units_by_product,
            "company_revenue_by_product": total_revenue_by_product,
            "aging_value_by_bucket": {k: round(v, 2) for k, v in aging_value.items()},
            "inventory_value_total": round(total_inv_value, 2),
            "store_performance": store_perf,
        }
