"""Tests for human-in-the-loop governance."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from retail_agents.governance import (
    GovernanceStore, Role, RecommendationState,
)


def _rec(**overrides) -> dict:
    base = {
        "recommendation_id": "REC-1",
        "store_id": "S101",
        "product_id": "P1",
        "action_type": "FRONT_OFFICE",
        "expected_margin_impact": 100.0,
        "created_at": "2026-11-03T07:00:00",
        "required_approval": "store_manager",
        "supporting_metrics": {},
    }
    base.update(overrides)
    return base


def test_intake_is_idempotent():
    s = GovernanceStore()
    a = s.intake(_rec())
    b = s.intake(_rec())
    assert a.idempotency_key == b.idempotency_key
    assert len(s.all()) == 1


def test_store_manager_approves_front_office():
    s = GovernanceStore()
    gov = s.intake(_rec())
    s.approve(gov.idempotency_key, actor="alice", actor_role=Role.STORE_MANAGER)
    assert gov.state == RecommendationState.APPROVED


def test_store_manager_cannot_approve_pricing():
    s = GovernanceStore()
    gov = s.intake(_rec(action_type="PRICING"))
    with pytest.raises(PermissionError):
        s.approve(gov.idempotency_key, actor="alice", actor_role=Role.STORE_MANAGER)


def test_high_margin_impact_auto_escalates():
    s = GovernanceStore()
    gov = s.intake(_rec(expected_margin_impact=1000.0))
    assert gov.required_role == Role.REGIONAL_MANAGER


def test_execute_requires_approval():
    s = GovernanceStore()
    gov = s.intake(_rec())
    with pytest.raises(ValueError):
        s.execute(gov.idempotency_key, actor="exec-svc")


def test_execute_is_idempotent():
    s = GovernanceStore()
    gov = s.intake(_rec())
    s.approve(gov.idempotency_key, "alice", Role.STORE_MANAGER)
    r1 = s.execute(gov.idempotency_key, "svc")
    r2 = s.execute(gov.idempotency_key, "svc")
    assert r1.executed_at == r2.executed_at
    assert r1.state == RecommendationState.EXECUTED


def test_expiry_moves_to_expired():
    s = GovernanceStore(ttl_hours=1)
    s.set_clock(datetime(2026, 11, 3, 7, 0, 0))
    gov = s.intake(_rec())
    s.set_clock(datetime(2026, 11, 3, 9, 0, 0))      # 2h later
    with pytest.raises(ValueError):
        s.approve(gov.idempotency_key, "alice", Role.STORE_MANAGER)
    assert gov.state == RecommendationState.EXPIRED


def test_audit_log_captures_states():
    s = GovernanceStore()
    gov = s.intake(_rec())
    s.approve(gov.idempotency_key, "alice", Role.STORE_MANAGER, reason="looks good")
    s.execute(gov.idempotency_key, "svc")
    actions = [a.action for a in gov.audit_log]
    assert actions == ["intake", "approved", "executed"]


def test_metrics_tracks_rates():
    s = GovernanceStore()
    g1 = s.intake(_rec(recommendation_id="A"))
    g2 = s.intake(_rec(recommendation_id="B", product_id="P2"))
    s.approve(g1.idempotency_key, "alice", Role.STORE_MANAGER)
    s.reject(g2.idempotency_key, "alice", Role.STORE_MANAGER, "no thanks")
    m = s.metrics()
    assert m["total"] == 2
    assert m["state_counts"]["approved"] == 1
    assert m["state_counts"]["rejected"] == 1
