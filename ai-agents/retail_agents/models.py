"""Dataclasses used across the agent system.

A `Recommendation` is the atomic unit the UI, the HTML report, and the
C# API all consume. It is deliberately self-describing — every field
required by the acceptance criteria (justification, metrics, impact,
confidence, priority, risks, approval) travels with the recommendation
itself, so downstream consumers never have to re-derive context.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


Priority = str  # "HIGH" | "MEDIUM" | "LOW"
ActionType = str


@dataclass
class Recommendation:
    recommendation_id: str
    store_id: str
    product_id: str | None
    action_type: ActionType  # e.g. FRONT_OFFICE, TRANSFER, MARKDOWN, PROMOTE, REPLENISH, REVIEW, PRICING, TARGET
    title: str
    justification: str
    supporting_metrics: dict[str, Any]
    expected_sales_impact: float
    expected_margin_impact: float
    confidence: float
    priority: Priority
    risks: list[str]
    assumptions: list[str]
    required_approval: str  # "store_manager" | "regional_manager" | "none"
    responsible_role: str
    deadline_hours: int
    success_kpi: str
    source_agent: str
    created_at: str = field(default_factory=lambda: datetime(2026, 11, 3, 7, 0, 0).isoformat())
    status: str = "pending"
    destination_store_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RecommendationBundle:
    store_id: str
    generated_at: str
    recommendations: list[Recommendation]
    agent_trace: list[dict]
    insights: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "store_id": self.store_id,
            "generated_at": self.generated_at,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "agent_trace": self.agent_trace,
            "insights": self.insights,
        }
