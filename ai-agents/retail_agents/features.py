"""Feature engineering shared across agents.

Produces the Gold-layer features that the business decision engine
needs: sales velocity, revenue, gross margin, inventory position,
return rate, and demand signals. Kept intentionally dependency-free so
it runs identically on the Databricks cluster and the local CSV path.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def product_sales_features(sales: list[dict], window_days: int = 90) -> dict[tuple[str, str], dict]:
    """Returns (store_id, product_id) -> aggregated sales features."""
    buckets: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"units": 0, "revenue": 0.0, "profit": 0.0, "txn": 0, "promo_units": 0}
    )
    for s in sales:
        key = (s["store_id"], s["product_id"])
        b = buckets[key]
        b["units"] += s["quantity"]
        b["revenue"] += s["revenue"]
        b["profit"] += s["gross_profit"]
        b["txn"] += 1
        if str(s.get("promotion_applied", "False")).lower() == "true":
            b["promo_units"] += s["quantity"]
    out = {}
    for k, b in buckets.items():
        weeks = window_days / 7.0
        velocity = b["units"] / weeks if weeks else 0
        margin = (b["profit"] / b["revenue"]) if b["revenue"] else 0
        out[k] = {
            "units_sold": b["units"],
            "revenue": round(b["revenue"], 2),
            "gross_profit": round(b["profit"], 2),
            "gross_margin_percent": round(margin * 100, 2),
            "weekly_velocity": round(velocity, 2),
            "transactions": b["txn"],
            "promo_unit_share": round(b["promo_units"] / b["units"], 3) if b["units"] else 0,
        }
    return out


def return_rate_features(sales: list[dict], returns: list[dict]) -> dict[tuple[str, str], float]:
    sold: dict[tuple[str, str], int] = defaultdict(int)
    returned: dict[tuple[str, str], int] = defaultdict(int)
    for s in sales:
        sold[(s["store_id"], s["product_id"])] += s["quantity"]
    for r in returns:
        returned[(r["store_id"], r["product_id"])] += r["quantity"]
    return {
        k: round(returned[k] / v, 4) if v else 0.0
        for k, v in sold.items()
    }


def survey_sentiment(surveys: list[dict]) -> dict[tuple[str, str], dict]:
    by_key: dict[tuple[str, str], list[int]] = defaultdict(list)
    for s in surveys:
        by_key[(s["store_id"], s["product_id"])].append(int(s["satisfaction_score"]))
    return {
        k: {
            "avg_satisfaction": round(mean(v), 2),
            "survey_count": len(v),
            "promoter_share": round(sum(1 for x in v if x >= 4) / len(v), 2),
        }
        for k, v in by_key.items()
    }


def demand_signal_by_product(trends: list[dict]) -> dict[str, float]:
    """Latest-week demand signal per product."""
    latest: dict[str, tuple[str, float]] = {}
    for t in trends:
        pid = t["product_id"]
        d = t["trend_date"]
        score = t["demand_signal_score"]
        if pid not in latest or d > latest[pid][0]:
            latest[pid] = (d, score)
    return {k: v[1] for k, v in latest.items()}


def inventory_aging_bucket(age_days: int) -> str:
    if age_days <= 30:
        return "0-30"
    if age_days <= 60:
        return "31-60"
    if age_days <= 90:
        return "61-90"
    if age_days <= 180:
        return "91-180"
    return "180+"


def enrich_inventory(inventory: list[dict]) -> list[dict]:
    for i in inventory:
        i["aging_bucket"] = inventory_aging_bucket(int(i["age_days"]))
        velocity = float(i["weekly_sales_velocity"])
        on_hand = int(i["on_hand_quantity"])
        i["weeks_of_cover"] = round(on_hand / velocity, 2) if velocity > 0 else float("inf")
        i["stockout_risk"] = velocity > 0 and on_hand < int(i["reorder_point"])
        i["excess_stock"] = velocity > 0 and (on_hand / velocity) > 10
    return inventory


def daily_sales_series(sales: list[dict], store_id: str) -> dict[str, float]:
    series: dict[str, float] = defaultdict(float)
    for s in sales:
        if s["store_id"] != store_id:
            continue
        series[s["transaction_date"]] += float(s["revenue"])
    return dict(sorted(series.items()))


def seven_day_forecast(series: dict[str, float]) -> list[dict]:
    """Simple seasonal-naive forecast: next day = same-day-of-week average
    across the trailing 4 weeks, then 7 days ahead. Explainable and
    deterministic; stronger models are documented but out of scope here."""
    if not series:
        return []
    dates = sorted(series.keys())
    last = _parse_date(dates[-1])
    # dow -> list of revenues from trailing 28 days
    trailing = {d: series[d] for d in dates[-28:]}
    dow_avg: dict[int, float] = defaultdict(list)
    for d_str, v in trailing.items():
        dow_avg[_parse_date(d_str).weekday()].append(v)
    dow_mean = {dow: (sum(vs) / len(vs)) for dow, vs in dow_avg.items()}
    out = []
    for i in range(1, 8):
        d = last + timedelta(days=i)
        baseline = dow_mean.get(d.weekday(), mean(trailing.values()))
        out.append(
            {
                "date": d.isoformat(),
                "baseline_forecast_revenue": round(baseline, 2),
                "recommended_target_revenue": round(baseline * 1.05, 2),
                "method": "seasonal_naive_dow",
            }
        )
    return out
