import pytest
from concurrent.futures import ThreadPoolExecutor
from .authorization_replay import AuthorizationReplayGuard, MAX_TOKENS, TOKEN_SIZE


def token(value=1):
    return value.to_bytes(TOKEN_SIZE, "big")


def test_token_is_single_use():
    guard = AuthorizationReplayGuard()
    assert guard.consume(token(), expires_at=200, now=100) is True
    assert guard.consume(token(), expires_at=200, now=100) is False
    assert guard.contains(token(), now=100) is True


def test_malformed_tokens_fail_closed():
    guard = AuthorizationReplayGuard()
    assert guard.consume(b"", expires_at=200, now=100) is False
    assert guard.consume(b"x" * (TOKEN_SIZE - 1), expires_at=200, now=100) is False
    assert guard.consume(b"x" * (TOKEN_SIZE + 1), expires_at=200, now=100) is False
    assert guard.consumed_count == 0


def test_capacity_is_bounded_and_fails_closed():
    guard = AuthorizationReplayGuard(max_tokens=2)
    assert guard.consume(token(1), expires_at=200, now=100) is True
    assert guard.consume(token(2), expires_at=200, now=100) is True
    assert guard.consume(token(3), expires_at=200, now=100) is False
    assert guard.consumed_count == 2


def test_maximum_capacity_is_policy_bounded():
    assert MAX_TOKENS == 1_000_000
    assert TOKEN_SIZE == 32
    for invalid in (0, MAX_TOKENS + 1, True, "1000000"):
        try:
            AuthorizationReplayGuard(max_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid capacity accepted")


def test_concurrent_consumers_only_one_wins():
    guard = AuthorizationReplayGuard()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: guard.consume(token(9), expires_at=200, now=100), range(64)))
    assert sum(results) == 1
    assert guard.consumed_count == 1



def test_expired_tokens_are_reclaimed_without_replay_window_overlap():
    guard = AuthorizationReplayGuard(max_tokens=1)
    assert guard.consume(token(1), expires_at=101, now=100)
    assert not guard.consume(token(2), expires_at=300, now=100)
    assert guard.contains(token(1), now=100)
    assert not guard.contains(token(1), now=101)
    assert guard.consume(token(2), expires_at=300, now=101)


def test_persistent_replay_guard_survives_restart_and_reclaims_expired_rows(tmp_path):
    path = str(tmp_path / "replay.sqlite3")
    first = AuthorizationReplayGuard(path=path, max_tokens=2)
    assert first.consume(token(11), expires_at=101, now=100)
    first.close()

    second = AuthorizationReplayGuard(path=path, max_tokens=2)
    assert second.contains(token(11), now=100)
    assert not second.consume(token(11), expires_at=200, now=100)
    assert second.consume(token(12), expires_at=200, now=101)
    assert second.consumed_count == 1
    second.close()


def test_expired_or_invalid_expiry_values_fail_closed():
    guard = AuthorizationReplayGuard()
    assert not guard.consume(token(1), expires_at=100, now=100)
    assert not guard.consume(token(2), expires_at=float("inf"), now=100)
    assert not guard.consume(token(3), expires_at=200, now=float("nan"))
    assert guard.consumed_count == 0



def test_persistent_replay_store_rejects_relative_and_symlink_paths(tmp_path):
    with pytest.raises(ValueError, match="absolute_replay_guard_path_required"):
        AuthorizationReplayGuard(path="relative-replay.sqlite3")

    target = tmp_path / "target.sqlite3"
    target.write_bytes(b"")
    link = tmp_path / "link.sqlite3"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink_path_rejected"):
        AuthorizationReplayGuard(path=str(link))


from .authorization_replay import AuthenticatedAuthorizationReplayGuard


def _authenticated_guard(db_path, *, key=b"k" * 32, key_id="test-key", max_tokens=8):
    return AuthenticatedAuthorizationReplayGuard(
        integrity_key=key, key_id=key_id, max_tokens=max_tokens, path=str(db_path)
    )


def test_authenticated_replay_guard_survives_restart(tmp_path):
    db_path = tmp_path / "authenticated-replay.sqlite3"
    first = _authenticated_guard(db_path)
    assert first.authenticated
    assert first.consume(token(101), expires_at=500, now=100)
    assert first.contains(token(101), now=100)
    first.close()
    second = _authenticated_guard(db_path)
    assert second.contains(token(101), now=100)
    assert not second.consume(token(101), expires_at=600, now=100)
    assert second.consumed_count == 1
    second.close()


def test_authenticated_replay_guard_detects_expiry_tampering(tmp_path):
    db_path = tmp_path / "tampered-expiry.sqlite3"
    guard = _authenticated_guard(db_path)
    assert guard.consume(token(102), expires_at=500, now=100)
    guard.close()
    import sqlite3
    db = sqlite3.connect(db_path)
    db.execute("UPDATE replay_guard_auth_tokens SET expires_at=900")
    db.commit()
    db.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        _authenticated_guard(db_path)


def test_authenticated_replay_guard_detects_mac_tampering(tmp_path):
    db_path = tmp_path / "tampered-mac.sqlite3"
    guard = _authenticated_guard(db_path)
    assert guard.consume(token(103), expires_at=500, now=100)
    guard.close()
    import sqlite3
    db = sqlite3.connect(db_path)
    db.execute("UPDATE replay_guard_auth_tokens SET record_mac=?", (b"x" * 32,))
    db.commit()
    db.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        _authenticated_guard(db_path)


def test_authenticated_replay_guard_rejects_wrong_key_or_key_id(tmp_path):
    db_path = tmp_path / "wrong-key.sqlite3"
    guard = _authenticated_guard(db_path)
    assert guard.consume(token(104), expires_at=500, now=100)
    guard.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        _authenticated_guard(db_path, key=b"z" * 32)
    with pytest.raises(RuntimeError, match="metadata_mismatch"):
        _authenticated_guard(db_path, key_id="rotated-key")


def test_authenticated_replay_guard_refuses_legacy_unkeyed_tokens(tmp_path):
    db_path = tmp_path / "legacy-replay.sqlite3"
    legacy = AuthorizationReplayGuard(path=str(db_path), max_tokens=8)
    assert legacy.consume(token(105), expires_at=500, now=100)
    legacy.close()
    with pytest.raises(RuntimeError, match="legacy_replay_tokens_require_explicit_migration"):
        _authenticated_guard(db_path)


def test_authenticated_replay_guard_reclaims_expired_authenticated_rows(tmp_path):
    db_path = tmp_path / "expired-authenticated.sqlite3"
    guard = _authenticated_guard(db_path, max_tokens=1)
    assert guard.consume(token(106), expires_at=101, now=100)
    assert not guard.consume(token(107), expires_at=500, now=100)
    assert guard.consume(token(107), expires_at=500, now=101)
    assert guard.consumed_count == 1
    guard.close()


def test_authenticated_replay_guard_rejects_short_key_and_memory_store(tmp_path):
    with pytest.raises(ValueError, match="integrity_key_too_short"):
        AuthenticatedAuthorizationReplayGuard(
            integrity_key=b"short", key_id="test", path=str(tmp_path / "short.sqlite3")
        )
    with pytest.raises(ValueError, match="persistent_replay_guard_path_required"):
        AuthenticatedAuthorizationReplayGuard(
            integrity_key=b"k" * 32, key_id="test", path=":memory:"
        )


from .actions import AuthorizationAuthority


def test_authority_can_require_authenticated_replay_guard(tmp_path):
    authenticated = _authenticated_guard(tmp_path / "authority-authenticated.sqlite3")
    authority = AuthorizationAuthority(
        b"a" * 32,
        replay_guard=authenticated,
        require_authenticated_replay=True,
    )
    assert authority.durable
    assert authority.integrity_protected
    assert authority.requires_authenticated_replay
    authenticated.close()


def test_authority_rejects_unkeyed_replay_guard_when_integrity_is_required(tmp_path):
    legacy = AuthorizationReplayGuard(
        path=str(tmp_path / "authority-legacy.sqlite3")
    )
    with pytest.raises(ValueError, match="authenticated_replay_guard_required"):
        AuthorizationAuthority(
            b"a" * 32,
            replay_guard=legacy,
            require_authenticated_replay=True,
        )
    legacy.close()


def test_authority_does_not_claim_authenticated_integrity_in_legacy_mode():
    authority = AuthorizationAuthority(b"a" * 32)
    assert authority.requires_authenticated_replay is False
    assert authority.integrity_protected is False


def test_consume_many_is_atomic_and_rejects_duplicate_batches():
    guard = AuthorizationReplayGuard(max_tokens=3)
    batch = (token(201), token(202))
    assert guard.consume_many(batch, expires_at=500, now=100) is True
    assert guard.consume_many(batch, expires_at=500, now=100) is False
    assert guard.consumed_count == 2
    assert guard.consume_many((token(203), token(204)), expires_at=500, now=100) is False
    assert guard.consumed_count == 2


def test_consume_many_rejects_duplicate_or_malformed_tokens_without_mutation():
    guard = AuthorizationReplayGuard(max_tokens=4)
    assert guard.consume_many((token(205), token(205)), expires_at=500, now=100) is False
    assert guard.consume_many((token(206), b"bad"), expires_at=500, now=100) is False
    assert guard.consumed_count == 0


def test_authenticated_consume_many_persists_all_or_none(tmp_path):
    path = tmp_path / "authenticated-batch.sqlite"
    guard = _authenticated_guard(path, max_tokens=4)
    batch = (token(207), token(208))
    assert guard.consume_many(batch, expires_at=500, now=100) is True
    assert guard.consumed_count == 2
    guard.close()

    reopened = _authenticated_guard(path, max_tokens=4)
    assert reopened.consume_many(batch, expires_at=500, now=100) is False
    assert reopened.consumed_count == 2
    reopened.close()


def test_authenticated_consume_many_fails_closed_on_tampered_expired_row(tmp_path):
    path = tmp_path / "authenticated-batch-tamper.sqlite"
    guard = _authenticated_guard(path)
    assert guard.consume(token(209), expires_at=101, now=100)
    guard.close()

    import sqlite3
    db = sqlite3.connect(path)
    db.execute("UPDATE replay_guard_auth_tokens SET expires_at=102")
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="integrity_failure"):
        _authenticated_guard(path)
