"""Inventory Optimization Agent — transfers, aging, replenishment.

Three concerns:
- Transfer from a store with excess to a store with stockout risk.
- Aging inventory: prefer margin-preserving actions before markdown.
- Replenishment: flag low-stock risk when weekly velocity > on-hand.
"""
from __future__ import annotations

from collections import defaultdict

from ..models import Recommendation
from ..tools import ToolRegistry


class InventoryOptimizationAgent:
    name = "InventoryOptimizationAgent"

    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    def recommend(self, store_id: str, insights: dict) -> list[Recommendation]:
        recs: list[Recommendation] = []
        recs.extend(self._transfer_recommendations(store_id, insights))
        recs.extend(self._aging_recommendations(store_id, insights))
        recs.extend(self._replenishment_recommendations(store_id, insights))
        return recs

    # --- Inter-store transfers (Scenario 2) ------------------------------
    def _transfer_recommendations(self, store_id: str, insights: dict) -> list[Recommendation]:
        all_inv = self.tools.call("get_inventory_position")
        products = insights["products"]
        by_prod: dict[str, list[dict]] = defaultdict(list)
        for r in all_inv:
            by_prod[r["product_id"]].append(r)

        proximity = {
            p["destination_store_id"]: p
            for p in self.tools.call("get_nearby_stores", store_id=store_id, max_distance_km=400)
        }
        recs = []
        local_inv = {r["product_id"]: r for r in insights["inventory"]}
        for pid, rows in by_prod.items():
            local = local_inv.get(pid)
            if not local:
                continue
            local_velocity = float(local["weekly_sales_velocity"])
            if local_velocity <= 0:
                continue
            local_oh = int(local["on_hand_quantity"])
            if local_oh >= local["reorder_point"] * 2:
                continue  # not stressed enough to transfer in
            best_source = None
            best_excess = 0
            for r in rows:
                if r["store_id"] == store_id:
                    continue
                src_velocity = float(r["weekly_sales_velocity"])
                src_oh = int(r["on_hand_quantity"])
                src_cover_weeks = (src_oh / src_velocity) if src_velocity > 0 else float("inf")
                if src_cover_weeks < 12:
                    continue
                excess = src_oh - int(src_velocity * 8)  # keep 8 weeks at source
                if excess > best_excess and r["store_id"] in proximity:
                    best_excess = excess
                    best_source = r
            if not best_source or best_excess < 5:
                continue

            need = max(0, int(local_velocity * 4) - local_oh)
            qty = min(best_excess, max(5, need))
            if qty <= 0:
                continue
            prox = proximity[best_source["store_id"]]
            product = products.get(pid, {})
            uplift_units = min(qty, int(local_velocity * 4))
            uplift_revenue = round(uplift_units * float(product.get("base_price", 0)), 2)
            margin_pct = _margin_percent(product)
            uplift_profit = round(uplift_revenue * margin_pct, 2)
            transfer_cost = round(qty * float(prox["transfer_cost_per_unit"]), 2)
            recs.append(
                Recommendation(
                    recommendation_id=f"REC-XFER-{best_source['store_id']}-{store_id}-{pid}",
                    store_id=store_id,
                    product_id=pid,
                    destination_store_id=store_id,
                    action_type="TRANSFER",
                    title=f"Transfer {qty}× {product.get('name', pid)} from {best_source['store_id']} to {store_id}",
                    justification=(
                        f"{store_id} sells {round(local_velocity, 1)}/wk with only {local_oh} on hand (<{local['reorder_point']} reorder); "
                        f"{best_source['store_id']} holds {int(best_source['on_hand_quantity'])} units at "
                        f"{round(float(best_source['weekly_sales_velocity']), 1)}/wk ({round(_weeks_cover(best_source), 1)} weeks of cover)."
                    ),
                    supporting_metrics={
                        "source_store_id": best_source["store_id"],
                        "source_on_hand": int(best_source["on_hand_quantity"]),
                        "source_weekly_velocity": float(best_source["weekly_sales_velocity"]),
                        "destination_on_hand": local_oh,
                        "destination_weekly_velocity": local_velocity,
                        "transfer_quantity": qty,
                        "distance_km": float(prox["distance_km"]),
                        "transfer_cost_estimate": transfer_cost,
                        "lead_time_days": int(prox["transfer_lead_time_days"]),
                    },
                    expected_sales_impact=uplift_revenue,
                    expected_margin_impact=round(uplift_profit - transfer_cost, 2),
                    confidence=0.78,
                    priority="HIGH",
                    risks=[
                        "Lead time exposes destination to short-term stockouts.",
                        "Transfer cost erodes margin if demand softens.",
                    ],
                    assumptions=[
                        "4 weeks of cover is the target for the destination store.",
                        "8 weeks of cover retained at the source store.",
                    ],
                    required_approval="regional_manager",
                    responsible_role="inventory_manager",
                    deadline_hours=48,
                    success_kpi="Destination stockout days after lead time",
                    source_agent=self.name,
                )
            )
        return recs

    # --- Aging inventory (Scenario 3) -----------------------------------
    def _aging_recommendations(self, store_id: str, insights: dict) -> list[Recommendation]:
        products = insights["products"]
        recs = []
        for r in insights["inventory"]:
            bucket = r["aging_bucket"]
            if bucket in ("0-30", "31-60"):
                continue
            pid = r["product_id"]
            product = products.get(pid, {})
            feats_key = f"{store_id}:{pid}"
            feats = insights["sales_by_product"].get(feats_key, {})
            velocity = float(r["weekly_sales_velocity"])
            on_hand = int(r["on_hand_quantity"])
            margin_pct = _margin_percent(product)
            action, justification, risks, approval, priority, title, uplift_rev, uplift_profit = _aging_action(
                bucket, velocity, on_hand, margin_pct, product
            )
            recs.append(
                Recommendation(
                    recommendation_id=f"REC-AGE-{store_id}-{pid}",
                    store_id=store_id,
                    product_id=pid,
                    action_type=action,
                    title=title,
                    justification=justification,
                    supporting_metrics={
                        "aging_bucket": bucket,
                        "age_days": int(r["age_days"]),
                        "on_hand_quantity": on_hand,
                        "weekly_velocity": velocity,
                        "weeks_of_cover": r["weeks_of_cover"] if r["weeks_of_cover"] != float("inf") else None,
                        "gross_margin_percent": feats.get("gross_margin_percent"),
                    },
                    expected_sales_impact=uplift_rev,
                    expected_margin_impact=uplift_profit,
                    confidence=0.65,
                    priority=priority,
                    risks=risks,
                    assumptions=["Aging-cohort uplift estimates based on retail planning heuristics, not a validated model."],
                    required_approval=approval,
                    responsible_role="store_manager",
                    deadline_hours=72,
                    success_kpi="Reduction in on-hand quantity within 14 days",
                    source_agent=self.name,
                )
            )
        return recs

    # --- Replenishment / stockout risk ----------------------------------
    def _replenishment_recommendations(self, store_id: str, insights: dict) -> list[Recommendation]:
        products = insights["products"]
        recs = []
        for r in insights["inventory"]:
            if not r["stockout_risk"]:
                continue
            pid = r["product_id"]
            product = products.get(pid, {})
            velocity = float(r["weekly_sales_velocity"])
            on_hand = int(r["on_hand_quantity"])
            short_qty = max(0, int(velocity * 4) - on_hand)
            if short_qty <= 0:
                continue
            margin_pct = _margin_percent(product)
            uplift_revenue = round(short_qty * float(product.get("base_price", 0)), 2)
            uplift_profit = round(uplift_revenue * margin_pct, 2)
            recs.append(
                Recommendation(
                    recommendation_id=f"REC-REPL-{store_id}-{pid}",
                    store_id=store_id,
                    product_id=pid,
                    action_type="REPLENISH",
                    title=f"Replenish {product.get('name', pid)} ({short_qty} units)",
                    justification=(
                        f"Weekly velocity {velocity} with only {on_hand} on hand (reorder point {r['reorder_point']}). "
                        f"Order quantity sized to 4 weeks of cover."
                    ),
                    supporting_metrics={
                        "on_hand_quantity": on_hand,
                        "weekly_velocity": velocity,
                        "reorder_point": r["reorder_point"],
                        "recommended_quantity": short_qty,
                    },
                    expected_sales_impact=uplift_revenue,
                    expected_margin_impact=uplift_profit,
                    confidence=0.72,
                    priority="HIGH",
                    risks=["Supplier lead time may delay availability.", "Over-ordering if demand softens."],
                    assumptions=["Supplier lead time ≤ 7 days."],
                    required_approval="inventory_manager",
                    responsible_role="inventory_manager",
                    deadline_hours=24,
                    success_kpi="Zero stockout days in next 14 days",
                    source_agent=self.name,
                )
            )
        return recs


def _weeks_cover(row: dict) -> float:
    v = float(row["weekly_sales_velocity"])
    return (int(row["on_hand_quantity"]) / v) if v > 0 else float("inf")


def _margin_percent(product: dict) -> float:
    base = float(product.get("base_price", 0))
    cost = float(product.get("cost", 0))
    return ((base - cost) / base) if base else 0.3


def _aging_action(bucket, velocity, on_hand, margin_pct, product):
    """Prefer margin-preserving actions before markdown."""
    base_price = float(product.get("base_price", 0))
    if bucket == "61-90" and velocity > 0.5:
        action = "FRONT_OFFICE"
        title = f"Reposition aging {product.get('name')} to front-office"
        just = f"Age {bucket} but still selling {velocity}/wk — visibility should accelerate sell-through."
        return action, just, ["Risk of cannibalizing featured products."], "store_manager", "MEDIUM", title, 0.0, 0.0
    if bucket == "91-180" and margin_pct > 0.3:
        action = "PROMOTE"
        title = f"Targeted promotion for aging {product.get('name')} (margin-safe)"
        just = f"Age {bucket}, margin {round(margin_pct*100,1)}% — a 10% targeted promotion preserves gross profit."
        uplift_rev = round(base_price * on_hand * 0.1, 2)
        uplift_profit = round(uplift_rev * (margin_pct - 0.1), 2)
        return action, just, ["Promotion may train customers to wait."], "store_manager", "MEDIUM", title, uplift_rev, uplift_profit
    if bucket == "91-180":
        action = "BUNDLE"
        title = f"Bundle {product.get('name')} with a complementary product"
        just = f"Age {bucket}, margin {round(margin_pct*100,1)}% is tight; bundling moves units without a direct markdown."
        return action, just, ["Bundle fit must be validated to avoid returns."], "store_manager", "MEDIUM", title, 0.0, 0.0
    # 180+
    if margin_pct > 0.4:
        action = "MARKDOWN"
        title = f"Controlled markdown on {product.get('name')} (15%)"
        just = f"Age {bucket}, margin {round(margin_pct*100,1)}%; a 15% markdown clears capital while preserving positive margin."
        uplift_rev = round(base_price * on_hand * 0.85, 2)
        uplift_profit = round(uplift_rev * (margin_pct - 0.15), 2)
        return action, just, ["Markdowns can set a lower reference price."], "regional_manager", "HIGH", title, uplift_rev, uplift_profit
    action = "CLEARANCE"
    title = f"Clearance plan for {product.get('name')}"
    just = f"Age {bucket} and margin is low; clearance frees capital and shelf space for higher-velocity products."
    return action, just, ["Perception risk if clearance is highly visible."], "regional_manager", "HIGH", title, 0.0, 0.0
