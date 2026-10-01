from core.provider_router import Provider
from core.provider_resilience import ResilientProviderExecutor

def test_provider_failover_uses_second_provider_after_first_failure():
    calls = []
    router = ResilientProviderExecutor(max_attempts=2)
    router.register(Provider("primary", frozenset({"chat"}), lambda p: (_ for _ in ()).throw(RuntimeError("down"))))
    router.register(Provider("secondary", frozenset({"chat"}), lambda p: calls.append(p) or {"ok": True}))
    result = router.execute("chat", {"message": "x"}, principal_id="user", logical_target="provider:chat", authorize=lambda p,c,t: True)
    assert result.provider == "secondary"
    assert result.output == {"ok": True}
    assert [a.provider for a in result.attempts] == ["primary", "secondary"]
    assert calls == [{"payload": {"message": "x"}}]

def test_provider_resilience_is_fail_closed_when_authorization_denied():
    calls = []
    router = ResilientProviderExecutor(max_attempts=2)
    router.register(Provider("primary", frozenset({"chat"}), lambda p: calls.append(p)))
    try:
        router.execute("chat", {}, principal_id="user", logical_target="provider:chat", authorize=lambda p,c,t: False)
    except PermissionError as exc:
        assert str(exc) == "execution_not_authorized"
    else:
        raise AssertionError("expected authorization denial")
    assert calls == []

def test_provider_resilience_exhaustion_is_bounded():
    router = ResilientProviderExecutor(max_attempts=2)
    router.register(Provider("only", frozenset({"chat"}), lambda p: (_ for _ in ()).throw(RuntimeError("down"))))
    try:
        router.execute("chat", {}, principal_id="user", logical_target="provider:chat", authorize=lambda p,c,t: True)
    except RuntimeError as exc:
        assert str(exc) == "provider_failover_exhausted"
    else:
        raise AssertionError("expected bounded failover exhaustion")
