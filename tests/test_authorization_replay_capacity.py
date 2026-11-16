from __future__ import annotations

import pytest

from core.actions import AuthorizationAuthority
from core.contracts import ActionSpec
from core.identity import AgentIdentityAuthority, IdentityRegistry


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


def context(clock, *, capacity=2, ttl=5.0):
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    registry = IdentityRegistry()
    registry.register(identity)
    authority = AuthorizationAuthority(
        b"k" * 32,
        clock=clock,
        max_ttl=10,
        identity_registry=registry,
        max_consumed_grants=capacity,
    )
    return identity, authority, ttl


def action(execution_id):
    return ActionSpec(
        action_id="publish-1",
        action_type="publish",
        target="resource-1",
        parameters={"content": "approved"},
        risk_class="sensitive",
        requires_authorization=True,
        execution_id=execution_id,
    )


def test_consumed_grant_is_one_shot_and_replay_cache_is_bounded():
    clock = Clock()
    identity, authority, ttl = context(clock, capacity=2)
    grants = []
    for index in range(2):
        spec = action(f"exec-{index}")
        grant = authority.issue(spec, spec.execution_id, principal=identity, ttl=ttl)
        assert authority.consume(spec, spec.execution_id, grant, principal=identity)
        assert not authority.consume(spec, spec.execution_id, grant, principal=identity)
        grants.append(grant)

    assert len(authority._used) == 2
    with pytest.raises(RuntimeError, match="authorization_replay_cache_full"):
        spec = action("exec-blocked")
        authority.issue(spec, spec.execution_id, principal=identity, ttl=ttl)


def test_expired_replay_entries_are_pruned_before_new_grants():
    clock = Clock()
    identity, authority, ttl = context(clock, capacity=1)
    spec = action("exec-1")
    grant = authority.issue(spec, spec.execution_id, principal=identity, ttl=ttl)
    assert authority.consume(spec, spec.execution_id, grant, principal=identity)
    assert len(authority._used) == 1

    clock.value += ttl + 0.01
    next_spec = action("exec-2")
    next_grant = authority.issue(next_spec, next_spec.execution_id, principal=identity, ttl=ttl)
    assert len(authority._used) == 0
    assert authority.consume(next_spec, next_spec.execution_id, next_grant, principal=identity)


def test_expiry_during_consume_does_not_reserve_nonce():
    clock = Clock()
    identity, authority, ttl = context(clock, capacity=1)
    spec = action("exec-expiring")
    grant = authority.issue(spec, spec.execution_id, principal=identity, ttl=ttl)
    clock.value += ttl
    assert not authority.consume(spec, spec.execution_id, grant, principal=identity)
    assert not authority._used


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5, 1_000_001])
def test_invalid_replay_cache_capacity_is_rejected(capacity):
    with pytest.raises(ValueError, match="invalid consumed grant capacity"):
        AuthorizationAuthority(b"k" * 32, max_consumed_grants=capacity)
