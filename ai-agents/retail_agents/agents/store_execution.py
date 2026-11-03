"""Store Execution Agent.

Takes validated recommendations and surfaces a prioritized action list.
It is concerned with ordering, owners, deadlines, and dependencies —
not with changing the underlying recommendations.
"""
from __future__ import annotations

from ..models import Recommendation


PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


class StoreExecutionAgent:
    name = "StoreExecutionAgent"

    def build_action_plan(self, recommendations: list[Recommendation]) -> list[dict]:
        recs = list(recommendations)
        recs.sort(
            key=lambda r: (
                PRIORITY_ORDER.get(r.priority, 3),
                -r.expected_margin_impact,
            )
        )
        plan = []
        for idx, r in enumerate(recs, start=1):
            plan.append(
                {
                    "sequence": idx,
                    "recommendation_id": r.recommendation_id,
                    "priority": r.priority,
                    "title": r.title,
                    "what": r.title,
                    "why": r.justification,
                    "owner": r.responsible_role,
                    "deadline_hours": r.deadline_hours,
                    "expected_sales_impact": r.expected_sales_impact,
                    "expected_margin_impact": r.expected_margin_impact,
                    "success_kpi": r.success_kpi,
                    "requires_approval": r.required_approval,
                    "status": r.status,
                }
            )
        return plan
