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
