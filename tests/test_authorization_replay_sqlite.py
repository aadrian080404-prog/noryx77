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
