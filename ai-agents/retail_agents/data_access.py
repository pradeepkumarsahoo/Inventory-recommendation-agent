"""Data access abstraction for the agent system.

Two adapters are provided:

- `LocalCsvAdapter` reads from `/databricks/sample-data`. This is the default and
  lets the full platform run locally with no cloud subscription.
- `DatabricksAdapter` is a config-driven stub that wires the same contract to
  the Databricks SQL warehouse via `databricks-sql-connector`. It is activated
  by setting `RETAIL_DATA_SOURCE=databricks` and the usual connection env vars
  (`DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN`). The adapter
  is intentionally not imported unless activated, so the stack has zero cloud
  dependency by default.

Both adapters expose a `RetailDataStore` facade so the agents never touch the
underlying source.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


DATA_DIR = Path(__file__).resolve().parents[2] / "databricks" / "sample-data"


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _coerce_numeric(rows: list[dict], numeric_fields: Iterable[str]):
    for r in rows:
        for k in numeric_fields:
            if k in r and r[k] != "":
                try:
                    r[k] = float(r[k]) if "." in r[k] else int(r[k])
                except ValueError:
                    pass
    return rows


class LocalCsvAdapter:
    """Reads sample CSVs. Pure-stdlib so no pandas dependency is required."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir

    @lru_cache(maxsize=1)
    def products(self) -> list[dict]:
        return _coerce_numeric(_read_csv(self.data_dir / "products.csv"), ["cost", "base_price", "trending_score"])

    @lru_cache(maxsize=1)
    def stores(self) -> list[dict]:
        return _coerce_numeric(_read_csv(self.data_dir / "stores.csv"), ["lat", "lon"])

    @lru_cache(maxsize=1)
    def store_proximity(self) -> list[dict]:
        return _coerce_numeric(
            _read_csv(self.data_dir / "store_proximity.csv"),
            ["distance_km", "transfer_lead_time_days", "transfer_cost_per_unit"],
        )

    @lru_cache(maxsize=1)
    def sales(self) -> list[dict]:
        return _coerce_numeric(
            _read_csv(self.data_dir / "sales.csv"),
            ["quantity", "unit_price", "revenue", "cost_total", "gross_profit"],
        )

    @lru_cache(maxsize=1)
    def inventory(self) -> list[dict]:
        return _coerce_numeric(
            _read_csv(self.data_dir / "inventory_snapshots.csv"),
            ["on_hand_quantity", "weekly_sales_velocity", "reorder_point", "age_days"],
        )

    @lru_cache(maxsize=1)
    def returns(self) -> list[dict]:
        return _coerce_numeric(_read_csv(self.data_dir / "returns.csv"), ["quantity", "refund_amount"])

    @lru_cache(maxsize=1)
    def surveys(self) -> list[dict]:
        return _coerce_numeric(_read_csv(self.data_dir / "surveys.csv"), ["satisfaction_score"])

    @lru_cache(maxsize=1)
    def trends(self) -> list[dict]:
        return _coerce_numeric(
            _read_csv(self.data_dir / "trends.csv"),
            ["social_mention_score", "search_interest_score", "demand_signal_score"],
        )

    @lru_cache(maxsize=1)
    def promotions(self) -> list[dict]:
        return _coerce_numeric(_read_csv(self.data_dir / "promotions.csv"), ["discount_percent"])

    @lru_cache(maxsize=1)
    def store_performance(self) -> list[dict]:
        return _coerce_numeric(
            _read_csv(self.data_dir / "store_performance.csv"),
            ["total_revenue", "total_gross_profit", "gross_margin_percent", "transaction_count", "avg_daily_revenue"],
        )


class DatabricksAdapter:
    """Databricks SQL adapter. Reads the same Gold tables under a workspace catalog.

    Keeping this adapter in-tree makes the Databricks integration path explicit
    without forcing the dependency on anyone running locally.
    """

    def __init__(self):
        self.host = os.environ["DATABRICKS_HOST"]
        self.http_path = os.environ["DATABRICKS_HTTP_PATH"]
        self.token = os.environ["DATABRICKS_TOKEN"]
        self.catalog = os.environ.get("DATABRICKS_CATALOG", "retail")
        self.schema = os.environ.get("DATABRICKS_SCHEMA", "gold")

    def _query(self, sql: str) -> list[dict]:  # pragma: no cover - integration path
        from databricks import sql as dbsql  # imported lazily
        with dbsql.connect(server_hostname=self.host, http_path=self.http_path, access_token=self.token) as c:
            with c.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def _ns(self, t: str) -> str:
        return f"{self.catalog}.{self.schema}.{t}"

    def products(self):
        return self._query(f"SELECT * FROM {self._ns('dim_product')}")

    def stores(self):
        return self._query(f"SELECT * FROM {self._ns('dim_store')}")

    def store_proximity(self):
        return self._query(f"SELECT * FROM {self._ns('store_proximity')}")

    def sales(self):
        return self._query(f"SELECT * FROM {self._ns('fact_sales')}")

    def inventory(self):
        return self._query(f"SELECT * FROM {self._ns('fact_inventory')}")

    def returns(self):
        return self._query(f"SELECT * FROM {self._ns('fact_returns')}")

    def surveys(self):
        return self._query(f"SELECT * FROM {self._ns('fact_customer_survey')}")

    def trends(self):
        return self._query(f"SELECT * FROM {self._ns('product_trend')}")

    def promotions(self):
        return self._query(f"SELECT * FROM {self._ns('promotions')}")

    def store_performance(self):
        return self._query(f"SELECT * FROM {self._ns('agg_store_performance_90d')}")


def _resolve_adapter():
    src = os.environ.get("RETAIL_DATA_SOURCE", "local").lower()
    if src == "databricks":  # pragma: no cover - integration path
        return DatabricksAdapter()
    return LocalCsvAdapter()


@dataclass
class RetailDataStore:
    """High-level facade with simple convenience lookups."""

    adapter: object = None

    def __post_init__(self):
        self.adapter = self.adapter or _resolve_adapter()

    # Direct passthroughs
    @property
    def products(self):
        return self.adapter.products()

    @property
    def stores(self):
        return self.adapter.stores()

    @property
    def store_proximity(self):
        return self.adapter.store_proximity()

    @property
    def sales(self):
        return self.adapter.sales()

    @property
    def inventory(self):
        return self.adapter.inventory()

    @property
    def returns(self):
        return self.adapter.returns()

    @property
    def surveys(self):
        return self.adapter.surveys()

    @property
    def trends(self):
        return self.adapter.trends()

    @property
    def promotions(self):
        return self.adapter.promotions()

    @property
    def store_performance(self):
        return self.adapter.store_performance()

    # Convenience lookups
    def product(self, product_id: str) -> dict:
        for p in self.products:
            if p["product_id"] == product_id:
                return p
        raise KeyError(product_id)

    def store(self, store_id: str) -> dict:
        for s in self.stores:
            if s["store_id"] == store_id:
                return s
        raise KeyError(store_id)
