import threading

from core.sqlite_authorization_replay import SQLiteAuthorizationReplayGuard


def test_replay_guard_persists_consumption_across_restart(tmp_path):
    db = tmp_path / "authorization-replay.db"
    first = SQLiteAuthorizationReplayGuard(db, max_tokens=4)
    token = b"a" * 32
    assert first.consume(token)
    assert first.contains(token)
    assert first.consumed_count == 1
    first.close()

    second = SQLiteAuthorizationReplayGuard(db, max_tokens=4)
    try:
        assert second.contains(token)
        assert not second.consume(token)
        assert second.consumed_count == 1
    finally:
        second.close()


def test_replay_guard_fails_closed_at_persistent_capacity(tmp_path):
    db = tmp_path / "authorization-replay-capacity.db"
    first = SQLiteAuthorizationReplayGuard(db, max_tokens=2)
    assert first.consume(b"a" * 32)
    assert first.consume(b"b" * 32)
    assert not first.consume(b"c" * 32)
    first.close()

    second = SQLiteAuthorizationReplayGuard(db, max_tokens=2)
    try:
        assert second.consumed_count == 2
        assert not second.consume(b"d" * 32)
    finally:
        second.close()


def test_two_independent_guards_consume_same_token_exactly_once(tmp_path):
    db = tmp_path / "authorization-replay-race.db"
    first = SQLiteAuthorizationReplayGuard(db, max_tokens=8)
    second = SQLiteAuthorizationReplayGuard(db, max_tokens=8)
    token = b"r" * 32
    barrier = threading.Barrier(2)
    outcomes = []
    lock = threading.Lock()

    def consume(guard):
        barrier.wait()
        result = guard.consume(token)
        with lock:
            outcomes.append(result)

    try:
        threads = [
            threading.Thread(target=consume, args=(first,)),
            threading.Thread(target=consume, args=(second,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert all(not thread.is_alive() for thread in threads)
        assert outcomes.count(True) == 1
        assert outcomes.count(False) == 1
        assert first.consumed_count == 1
    finally:
        first.close()
        second.close()


def test_replay_guard_rejects_malformed_tokens(tmp_path):
    guard = SQLiteAuthorizationReplayGuard(tmp_path / "authorization-replay-invalid.db")
    try:
        assert not guard.consume(b"short")
        assert not guard.contains(b"short")
        assert guard.consumed_count == 0
    finally:
        guard.close()
