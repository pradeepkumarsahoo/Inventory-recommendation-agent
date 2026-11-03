"""Backend-grounded tools exposed to the agent system.

Every tool is a plain Python function whose inputs are JSON-serializable.
They are the ONLY way an agent is allowed to read business data, which
means every recommendation can be traced back to a tool call. The LLM
path serializes these calls through the guardrail layer; the
deterministic path invokes them directly.

Nothing in this module writes data. Execution of consequential actions
(transfers, pricing changes, promotions) is a separate concern handled by
the C# API, after human approval.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .data_access import RetailDataStore
from .features import (
    enrich_inventory,
    product_sales_features,
    return_rate_features,
    survey_sentiment,
    demand_signal_by_product,
    seven_day_forecast,
    daily_sales_series,
)


class ToolRegistry:
    """Explicit tool catalog with JSON schemas, usable by an LLM or test suite."""

    def __init__(self, store: RetailDataStore | None = None):
        self.store = store or RetailDataStore()
        self._registry = {}
        self._register_all()

    def _register_all(self):
        self.register(
            "get_product_catalog",
            self.get_product_catalog,
            "Return the full product master data.",
            {"type": "object", "properties": {}, "required": []},
        )
        self.register(
            "get_store_catalog",
            self.get_store_catalog,
            "Return the store master data including geographic info.",
            {"type": "object", "properties": {}, "required": []},
        )
        self.register(
            "get_sales_summary",
            self.get_sales_summary,
            "Return per (store, product) 90-day sales features.",
            {"type": "object", "properties": {"store_id": {"type": "string"}}, "required": []},
        )
        self.register(
            "get_inventory_position",
            self.get_inventory_position,
            "Return inventory with aging bucket, weeks of cover, risk flags.",
            {"type": "object", "properties": {"store_id": {"type": "string"}}, "required": []},
        )
        self.register(
            "get_return_rates",
            self.get_return_rates,
            "Return return-rate per (store, product).",
            {"type": "object", "properties": {}, "required": []},
        )
        self.register(
            "get_survey_sentiment",
            self.get_survey_sentiment,
            "Return customer satisfaction aggregated per (store, product).",
            {"type": "object", "properties": {}, "required": []},
        )
        self.register(
            "get_trending_products",
            self.get_trending_products,
            "Return the latest demand signal per product.",
            {"type": "object", "properties": {}, "required": []},
        )
        self.register(
            "get_nearby_stores",
            self.get_nearby_stores,
            "Return stores within distance_km of store_id with transfer logistics.",
            {
                "type": "object",
                "properties": {"store_id": {"type": "string"}, "max_distance_km": {"type": "number"}},
                "required": ["store_id"],
            },
        )
        self.register(
            "get_store_forecast",
            self.get_store_forecast,
            "Return a 7-day revenue forecast and target recommendation for a store.",
            {"type": "object", "properties": {"store_id": {"type": "string"}}, "required": ["store_id"]},
        )

    def register(self, name: str, fn, description: str, schema: dict):
        self._registry[name] = {"fn": fn, "description": description, "schema": schema}

    def describe(self) -> list[dict]:
        return [
            {"name": n, "description": v["description"], "input_schema": v["schema"]}
            for n, v in self._registry.items()
        ]

    def call(self, name: str, **kwargs) -> Any:
        if name not in self._registry:
            raise KeyError(f"Unknown tool: {name}")
        return self._registry[name]["fn"](**kwargs)

    # ---- Tool implementations --------------------------------------------
    def get_product_catalog(self) -> list[dict]:
        return self.store.products

    def get_store_catalog(self) -> list[dict]:
        return self.store.stores

    def get_sales_summary(self, store_id: str | None = None):
        feats = product_sales_features(self.store.sales)
        if store_id:
            return {f"{k[0]}:{k[1]}": v for k, v in feats.items() if k[0] == store_id}
        return {f"{k[0]}:{k[1]}": v for k, v in feats.items()}

    def get_inventory_position(self, store_id: str | None = None):
        inv = enrich_inventory([dict(r) for r in self.store.inventory])
        if store_id:
            inv = [r for r in inv if r["store_id"] == store_id]
        return inv

    def get_return_rates(self):
        return {f"{k[0]}:{k[1]}": v for k, v in return_rate_features(self.store.sales, self.store.returns).items()}

    def get_survey_sentiment(self):
        return {f"{k[0]}:{k[1]}": v for k, v in survey_sentiment(self.store.surveys).items()}

    def get_trending_products(self):
        return demand_signal_by_product(self.store.trends)

    def get_nearby_stores(self, store_id: str, max_distance_km: float = 400.0):
        return [
            p for p in self.store.store_proximity
            if p["source_store_id"] == store_id and float(p["distance_km"]) <= max_distance_km
        ]

    def get_store_forecast(self, store_id: str):
        series = daily_sales_series(self.store.sales, store_id)
        forecast = seven_day_forecast(series)
        return {
            "store_id": store_id,
            "trailing_7d_revenue": sum(list(series.values())[-7:]),
            "forecast": forecast,
        }
