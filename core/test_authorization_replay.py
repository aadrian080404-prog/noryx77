from concurrent.futures import ThreadPoolExecutor

from .authorization_replay import AuthorizationReplayGuard, MAX_TOKENS, TOKEN_SIZE


def token(value=1):
    return value.to_bytes(TOKEN_SIZE, "big")


def test_token_is_single_use():
    guard = AuthorizationReplayGuard()
    assert guard.consume(token()) is True
    assert guard.consume(token()) is False
    assert guard.contains(token()) is True


def test_malformed_tokens_fail_closed():
    guard = AuthorizationReplayGuard()
    assert guard.consume(b"") is False
    assert guard.consume(b"x" * (TOKEN_SIZE - 1)) is False
    assert guard.consume(b"x" * (TOKEN_SIZE + 1)) is False
    assert guard.consumed_count == 0


def test_capacity_is_bounded_and_fails_closed():
    guard = AuthorizationReplayGuard(max_tokens=2)
    assert guard.consume(token(1)) is True
    assert guard.consume(token(2)) is True
    assert guard.consume(token(3)) is False
    assert guard.consumed_count == 2


def test_maximum_capacity_is_policy_bounded():
    assert MAX_TOKENS == 4096
    assert TOKEN_SIZE == 32
    for invalid in (0, MAX_TOKENS + 1, True, "4096"):
        try:
            AuthorizationReplayGuard(max_tokens=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid capacity accepted")


def test_concurrent_consumers_only_one_wins():
    guard = AuthorizationReplayGuard()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: guard.consume(token(9)), range(64)))
    assert sum(results) == 1
    assert guard.consumed_count == 1
