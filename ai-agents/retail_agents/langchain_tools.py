"""LangChain wrappers around the backend-grounded ToolRegistry.

Every retail data read is exposed to a LangChain agent as a `StructuredTool`,
so an LLM-driven supervisor can reason about which tool to call next while
still being locked to the deterministic, auditable backend functions.

Design intent:
- The LLM NEVER touches raw datasets. It only calls these tool shims.
- Every tool call returns JSON-serializable output so it can be logged for audit.
- Argument schemas are declared with Pydantic so the agent gets precise
  tool signatures (fewer hallucinated arguments).
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

try:  # LangChain is optional at import time
    from langchain_core.tools import StructuredTool
except Exception:  # pragma: no cover - import guard
    StructuredTool = None  # type: ignore

from .tools import ToolRegistry


# ---------- Pydantic argument schemas ---------------------------------------

class _NoArgs(BaseModel):
    pass


class _StoreIdOnly(BaseModel):
    store_id: Optional[str] = Field(default=None, description="Store identifier, e.g. S101")


class _StoreIdRequired(BaseModel):
    store_id: str = Field(..., description="Store identifier, e.g. S101")


class _NearbyStoresArgs(BaseModel):
    store_id: str = Field(..., description="Source store identifier")
    max_distance_km: float = Field(default=400.0, description="Maximum distance in km")


# ---------- Public factory --------------------------------------------------

def build_langchain_tools(registry: ToolRegistry) -> list[Any]:
    """Return a list of LangChain `StructuredTool`s bound to `registry`."""
    if StructuredTool is None:
        raise ImportError(
            "LangChain is not installed. Install with: pip install langchain langchain-core"
        )

    def _wrap(name: str, args_schema: type[BaseModel], description: str):
        def _invoke(**kwargs):
            return registry.call(name, **{k: v for k, v in kwargs.items() if v is not None})
        _invoke.__name__ = name
        return StructuredTool.from_function(
            func=_invoke,
            name=name,
            description=description,
            args_schema=args_schema,
        )

    return [
        _wrap("get_product_catalog", _NoArgs, "Return the full product master data."),
        _wrap("get_store_catalog", _NoArgs, "Return the store master data."),
        _wrap("get_sales_summary", _StoreIdOnly, "Return per (store, product) 90-day sales features."),
        _wrap("get_inventory_position", _StoreIdOnly, "Return inventory with aging/weeks-of-cover."),
        _wrap("get_return_rates", _NoArgs, "Return return-rate per (store, product)."),
        _wrap("get_survey_sentiment", _NoArgs, "Return customer satisfaction per (store, product)."),
        _wrap("get_trending_products", _NoArgs, "Return the latest demand signal per product."),
        _wrap("get_nearby_stores", _NearbyStoresArgs, "Return stores within distance_km of store_id."),
        _wrap("get_store_forecast", _StoreIdRequired, "Return a 7-day revenue forecast for a store."),
    ]
