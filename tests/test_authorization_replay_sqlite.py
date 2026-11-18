from concurrent.futures import ThreadPoolExecutor

import pytest

from core.authorization_replay import SQLiteAuthorizationReplayGuard


def test_sqlite_replay_guard_survives_reconstruction(tmp_path):
    database = tmp_path / "replay.db"
    first = SQLiteAuthorizationReplayGuard(database, max_tokens=8)
    token = b"A" * 32

    assert first.consume(token)
    assert first.contains(token)
    assert first.consumed_count == 1

    reopened = SQLiteAuthorizationReplayGuard(database, max_tokens=8)
    assert reopened.contains(token)
    assert not reopened.consume(token)
    assert reopened.consumed_count == 1


def test_sqlite_replay_guard_coordinates_independent_instances(tmp_path):
    database = tmp_path / "shared-replay.db"
    guards = [
        SQLiteAuthorizationReplayGuard(database, max_tokens=32)
        for _ in range(8)
    ]
    token = b"B" * 32

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda guard: guard.consume(token), guards))

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert guards[0].consumed_count == 1


def test_sqlite_replay_guard_enforces_capacity_without_eviction(tmp_path):
    database = tmp_path / "bounded-replay.db"
    guard = SQLiteAuthorizationReplayGuard(database, max_tokens=2)

    assert guard.consume(b"C" * 32)
    assert guard.consume(b"D" * 32)
    assert not guard.consume(b"E" * 32)
    assert not guard.consume(b"C" * 32)
    assert guard.consumed_count == 2


def test_sqlite_replay_guard_rejects_malformed_tokens(tmp_path):
    guard = SQLiteAuthorizationReplayGuard(tmp_path / "malformed.db")

    assert not guard.consume(b"short")
    assert not guard.contains(b"short")
    assert guard.consumed_count == 0


def test_sqlite_replay_guard_rejects_capacity_mismatch(tmp_path):
    database = tmp_path / "configuration.db"
    SQLiteAuthorizationReplayGuard(database, max_tokens=4)

    with pytest.raises(ValueError, match="replay_store_configuration_mismatch"):
        SQLiteAuthorizationReplayGuard(database, max_tokens=5)


def test_sqlite_replay_guard_requires_persistent_storage():
    with pytest.raises(ValueError, match="persistent_replay_database_required"):
        SQLiteAuthorizationReplayGuard(":memory:")



def _authorized_action():
    from core.contracts import ActionSpec
    return ActionSpec(
        action_id="action-1",
        action_type="write",
        target="local-resource",
        parameters={"value": 1},
        risk_class="high",
        requires_authorization=True,
        execution_id="execution-1",
    )


def test_authorization_authority_uses_durable_replay_guard_across_restarts(tmp_path):
    from core.actions import AuthorizationAuthority

    database = tmp_path / "authority-replay.sqlite3"
    secret = b"N" * 32
    action = _authorized_action()
    first = AuthorizationAuthority(
        secret,
        replay_guard=SQLiteAuthorizationReplayGuard(database, max_tokens=16),
    )
    grant = first.issue(action, "execution-1")
    assert first.verify(action, "execution-1", grant)
    assert first.consume(action, "execution-1", grant)

    reopened = AuthorizationAuthority(
        secret,
        replay_guard=SQLiteAuthorizationReplayGuard(database, max_tokens=16),
    )
    assert not reopened.verify(action, "execution-1", grant)
    assert not reopened.consume(action, "execution-1", grant)


def test_authorization_authority_fails_closed_when_durable_replay_store_is_full(tmp_path):
    from core.actions import AuthorizationAuthority

    database = tmp_path / "authority-full.sqlite3"
    secret = b"M" * 32
    action = _authorized_action()
    authority = AuthorizationAuthority(
        secret,
        replay_guard=SQLiteAuthorizationReplayGuard(database, max_tokens=1),
    )
    first = authority.issue(action, "execution-1")
    second = authority.issue(action, "execution-1")
    assert authority.consume(action, "execution-1", first)
    assert not authority.verify(action, "execution-1", second)
    assert not authority.consume(action, "execution-1", second)



def test_authorized_dispatch_consumes_durable_grant_before_executor(tmp_path):
    from core.actions import AuthorizationAuthority
    from core.identity import AgentIdentityAuthority, IdentityRegistry

    registry = IdentityRegistry()
    principal, _private_key = AgentIdentityAuthority.generate("dispatch-principal")
    registry.register(principal)
    database = tmp_path / "dispatch-replay.sqlite3"
    secret = b"P" * 32
    action = _authorized_action()
    authority = AuthorizationAuthority(
        secret,
        identity_registry=registry,
        replay_guard=SQLiteAuthorizationReplayGuard(database, max_tokens=8),
    )
    grant = authority.issue(action, "execution-1", principal=principal)
    calls = []
    consumed, result = authority.consume_and_execute(
        action, "execution-1", grant, principal,
        lambda: calls.append("executed") or "ok",
    )
    assert consumed is True
    assert result == "ok"
    assert calls == ["executed"]

    reopened = AuthorizationAuthority(
        secret,
        identity_registry=registry,
        replay_guard=SQLiteAuthorizationReplayGuard(database, max_tokens=8),
    )
    consumed_again, result_again = reopened.consume_and_execute(
        action, "execution-1", grant, principal,
        lambda: calls.append("replayed"),
    )
    assert consumed_again is False
    assert result_again is None
    assert calls == ["executed"]
