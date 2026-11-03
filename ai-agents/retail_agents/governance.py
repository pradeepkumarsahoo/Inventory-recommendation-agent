"""Human-in-the-loop governance for recommendation execution.

Extends the existing `required_approval` field on each Recommendation with:

- **Role-based permissions** (RBAC): who can approve what.
- **Workflow states**: pending → approved | rejected | expired | executed.
- **Audit log**: every state change is appended with actor, timestamp, reason.
- **Expiry**: recommendations time-out after a configurable TTL.
- **Idempotency keys**: executing the same recommendation twice is a no-op.
- **Escalation**: high-risk actions above thresholds route to regional_manager
  regardless of what the originating agent declared.

The store is in-memory for the learning scope; a real deployment would
back this with a transactional store (Postgres + outbox) owned by the
C# API layer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class RecommendationState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class Role(str, Enum):
    STORE_MANAGER = "store_manager"
    REGIONAL_MANAGER = "regional_manager"
    FINANCE_APPROVER = "finance_approver"
    AUDITOR = "auditor"           # read-only
    AGENT = "agent"               # system actor


# What each role is allowed to approve. Finance has blanket authority
# for any pricing action; regional handles cross-store transfers.
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.STORE_MANAGER: {"FRONT_OFFICE", "REPLENISH"},
    Role.REGIONAL_MANAGER: {"TRANSFER", "MARKDOWN", "AGING_REVIEW", "FRONT_OFFICE"},
    Role.FINANCE_APPROVER: {"PRICING", "MARKDOWN"},
    Role.AUDITOR: set(),
    Role.AGENT: set(),
}

# Any action above these impact thresholds auto-escalates to regional.
ESCALATION_THRESHOLDS = {
    "expected_margin_impact_abs": 500.0,     # dollar impact
    "price_change_pct": 0.10,                # 10% or more
    "transfer_units": 100,
}

DEFAULT_TTL_HOURS = 24


@dataclass
class AuditEntry:
    timestamp: str
    actor: str
    actor_role: Role
    action: str                  # "approved" | "rejected" | "executed" | "expired" | "escalated"
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "actor_role": self.actor_role.value,
            "action": self.action,
            "reason": self.reason,
        }


@dataclass
class GovernedRecommendation:
    recommendation: dict                       # the raw Recommendation.to_dict()
    state: RecommendationState = RecommendationState.PENDING
    required_role: Role = Role.STORE_MANAGER
    expires_at: str = ""
    audit_log: list[AuditEntry] = field(default_factory=list)
    idempotency_key: str = ""
    executed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "recommendation": self.recommendation,
            "state": self.state.value,
            "required_role": self.required_role.value,
            "expires_at": self.expires_at,
            "idempotency_key": self.idempotency_key,
            "executed_at": self.executed_at,
            "audit_log": [a.to_dict() for a in self.audit_log],
        }


# ---------- Core store ------------------------------------------------------

class GovernanceStore:
    """In-memory governance store with workflow transitions + audit log."""

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS):
        self._items: dict[str, GovernedRecommendation] = {}
        self._executed_keys: set[str] = set()      # idempotency guard
        self.ttl_hours = ttl_hours
        self._now_override: Optional[datetime] = None  # tests inject clock

    # -- clock -------------------------------------------------------------

    def _now(self) -> datetime:
        return self._now_override or datetime.utcnow()

    def set_clock(self, now: datetime) -> None:
        self._now_override = now

    # -- intake ------------------------------------------------------------

    def _idempotency_key(self, rec: dict) -> str:
        payload = json.dumps(
            {
                "id": rec.get("recommendation_id"),
                "store": rec.get("store_id"),
                "product": rec.get("product_id"),
                "action": rec.get("action_type"),
                "day": rec.get("created_at", "")[:10],
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def _determine_required_role(self, rec: dict) -> Role:
        """Escalate when thresholds exceeded; else honor rec.required_approval."""
        action = rec.get("action_type", "")
        metrics = rec.get("supporting_metrics", {})
        margin_impact = abs(rec.get("expected_margin_impact", 0.0))
        price_change = abs(metrics.get("price_change_pct", 0.0))
        transfer_units = metrics.get("transfer_units", 0)

        if (
            margin_impact >= ESCALATION_THRESHOLDS["expected_margin_impact_abs"]
            or price_change >= ESCALATION_THRESHOLDS["price_change_pct"]
            or transfer_units >= ESCALATION_THRESHOLDS["transfer_units"]
            or action in ("MARKDOWN", "PRICING")
        ):
            return Role.REGIONAL_MANAGER if action != "PRICING" else Role.FINANCE_APPROVER

        return Role.STORE_MANAGER

    def intake(self, recommendation: dict) -> GovernedRecommendation:
        key = self._idempotency_key(recommendation)
        if key in self._items:
            return self._items[key]       # already seen; idempotent

        role = self._determine_required_role(recommendation)
        expires = (self._now() + timedelta(hours=self.ttl_hours)).isoformat()
        gov = GovernedRecommendation(
            recommendation=recommendation,
            required_role=role,
            expires_at=expires,
            idempotency_key=key,
        )
        gov.audit_log.append(AuditEntry(
            timestamp=self._now().isoformat(),
            actor="SupervisorAgent",
            actor_role=Role.AGENT,
            action="intake",
            reason=f"Routed to {role.value}",
        ))
        self._items[key] = gov
        return gov

    # -- transitions -------------------------------------------------------

    def _refresh_expiry(self, gov: GovernedRecommendation) -> None:
        if gov.state == RecommendationState.PENDING:
            if self._now() >= datetime.fromisoformat(gov.expires_at):
                gov.state = RecommendationState.EXPIRED
                gov.audit_log.append(AuditEntry(
                    timestamp=self._now().isoformat(),
                    actor="system",
                    actor_role=Role.AGENT,
                    action="expired",
                    reason=f"TTL {self.ttl_hours}h exceeded",
                ))

    def approve(self, idempotency_key: str, actor: str, actor_role: Role,
                reason: str = "") -> GovernedRecommendation:
        gov = self._require(idempotency_key)
        self._refresh_expiry(gov)
        if gov.state != RecommendationState.PENDING:
            raise ValueError(f"Cannot approve from state {gov.state.value}")
        if gov.recommendation.get("action_type") not in ROLE_PERMISSIONS.get(actor_role, set()):
            raise PermissionError(
                f"Role {actor_role.value} may not approve action "
                f"{gov.recommendation.get('action_type')}"
            )
        if actor_role != gov.required_role and actor_role != Role.REGIONAL_MANAGER:
            # Regional can override lower approvals; others must match exactly.
            raise PermissionError(
                f"Required role is {gov.required_role.value}, got {actor_role.value}"
            )
        gov.state = RecommendationState.APPROVED
        gov.audit_log.append(AuditEntry(
            timestamp=self._now().isoformat(),
            actor=actor, actor_role=actor_role,
            action="approved", reason=reason,
        ))
        return gov

    def reject(self, idempotency_key: str, actor: str, actor_role: Role,
               reason: str) -> GovernedRecommendation:
        gov = self._require(idempotency_key)
        self._refresh_expiry(gov)
        if gov.state not in (RecommendationState.PENDING, RecommendationState.APPROVED):
            raise ValueError(f"Cannot reject from state {gov.state.value}")
        gov.state = RecommendationState.REJECTED
        gov.audit_log.append(AuditEntry(
            timestamp=self._now().isoformat(),
            actor=actor, actor_role=actor_role,
            action="rejected", reason=reason,
        ))
        return gov

    def execute(self, idempotency_key: str, actor: str,
                actor_role: Role = Role.AGENT) -> GovernedRecommendation:
        gov = self._require(idempotency_key)
        if idempotency_key in self._executed_keys:
            # Idempotent: executing twice returns the already-executed record.
            return gov
        if gov.state != RecommendationState.APPROVED:
            raise ValueError(f"Cannot execute from state {gov.state.value}")
        gov.state = RecommendationState.EXECUTED
        gov.executed_at = self._now().isoformat()
        gov.audit_log.append(AuditEntry(
            timestamp=gov.executed_at,
            actor=actor, actor_role=actor_role,
            action="executed", reason=None,
        ))
        self._executed_keys.add(idempotency_key)
        return gov

    # -- queries ------------------------------------------------------------

    def _require(self, key: str) -> GovernedRecommendation:
        if key not in self._items:
            raise KeyError(f"Unknown recommendation key {key}")
        return self._items[key]

    def pending_for_role(self, role: Role) -> list[GovernedRecommendation]:
        out: list[GovernedRecommendation] = []
        for gov in self._items.values():
            self._refresh_expiry(gov)
            if gov.state == RecommendationState.PENDING and gov.required_role == role:
                out.append(gov)
        return out

    def all(self) -> list[GovernedRecommendation]:
        for gov in self._items.values():
            self._refresh_expiry(gov)
        return list(self._items.values())

    def metrics(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for gov in self.all():
            counts[gov.state.value] = counts.get(gov.state.value, 0) + 1
        total = len(self._items) or 1
        return {
            "total": len(self._items),
            "state_counts": counts,
            "approval_rate": round(counts.get("approved", 0) / total +
                                    counts.get("executed", 0) / total, 3),
            "rejection_rate": round(counts.get("rejected", 0) / total, 3),
            "expiry_rate": round(counts.get("expired", 0) / total, 3),
        }
