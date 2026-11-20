from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.contracts import ActionSpec
from core.principal_identity import PrincipalIdentity
from core.principal_authorization import PrincipalAuthorizationAuthority
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry


def _setup(tmp_path, clock=lambda: 100):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    identity = PrincipalIdentity("tenant-1", public)
    registry = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite")
    registry.register(identity)
    authority = PrincipalAuthorizationAuthority(
        b"s" * 32, tmp_path / "grants.sqlite", registry, clock=clock
    )
    action = ActionSpec(
        action_id="read-1", action_type="memory.read", target="memory",
        parameters={"scope": "private"}, risk_class="high",
        requires_authorization=True, execution_id="exec-1",
    )
    return registry, authority, action


def test_principal_grant_is_bound_and_consumed_once(tmp_path):
    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    called = []
    assert authority.consume_and_execute(
        action, "exec-1", grant, lambda: called.append("run") or "ok"
    ) == (True, "ok")
    assert called == ["run"]
    assert authority.consume_and_execute(action, "exec-1", grant, lambda: called.append("again")) == (False, None)
    assert called == ["run"]


def test_principal_grant_rejects_action_substitution(tmp_path):
    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    changed = ActionSpec(
        action_id="read-1", action_type="memory.read", target="other-memory",
        parameters={"scope": "private"}, risk_class="high",
        requires_authorization=True, execution_id="exec-1",
    )
    assert authority.consume_and_execute(changed, "exec-1", grant, lambda: "unsafe") == (False, None)


def test_principal_grant_rejects_revoked_principal(tmp_path):
    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    registry.revoke("tenant-1")
    assert authority.consume_and_execute(action, "exec-1", grant, lambda: "unsafe") == (False, None)


def test_principal_grant_rejects_expired_grant(tmp_path):
    now = [100]
    registry, authority, action = _setup(tmp_path, clock=lambda: now[0])
    grant = authority.issue(action, "exec-1", "tenant-1", ttl_seconds=2)
    now[0] = 102
    assert authority.consume_and_execute(action, "exec-1", grant, lambda: "unsafe") == (False, None)


def test_principal_grant_survives_authority_restart_but_not_replay(tmp_path):
    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    restarted = PrincipalAuthorizationAuthority(
        b"s" * 32, tmp_path / "grants.sqlite", registry, clock=lambda: 100
    )
    assert restarted.consume_and_execute(action, "exec-1", grant, lambda: "after-restart") == (True, "after-restart")
    assert authority.consume_and_execute(action, "exec-1", grant, lambda: "duplicate") == (False, None)


def test_concurrent_dispatch_consumes_grant_at_most_once(tmp_path):
    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    called = []

    def dispatch():
        return authority.consume_and_execute(
            action, "exec-1", grant, lambda: called.append("run") or "ok"
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: dispatch(), range(2)))

    assert sum(1 for consumed, _ in results if consumed) == 1
    assert called == ["run"]


def test_principal_grant_expires_while_waiting_for_registry_lock(tmp_path):
    now = [100]
    registry, authority, action = _setup(tmp_path, clock=lambda: now[0])
    grant = authority.issue(action, "exec-1", "tenant-1", ttl_seconds=1)
    original = registry.with_trusted_principal

    def delayed_with_trusted_principal(principal_id, callback):
        def advance_clock(identity):
            now[0] = 101
            return callback(identity)
        return original(principal_id, advance_clock)

    registry.with_trusted_principal = delayed_with_trusted_principal
    called = []
    assert authority.consume_and_execute(
        action, "exec-1", grant, lambda: called.append("unsafe")
    ) == (False, None)
    assert called == []

def _consume_grant_in_process(authority, action, grant, start, results, marker):
    start.wait(timeout=10)
    try:
        accepted, value = authority.consume_and_execute(
            action, "exec-1", grant, lambda: marker
        )
        results.put((accepted, value))
    except Exception as exc:
        results.put(("error", type(exc).__name__))


def test_independent_processes_consume_persisted_grant_at_most_once(tmp_path):
    from multiprocessing import get_all_start_methods, get_context
    from queue import Empty

    import pytest

    if "fork" not in get_all_start_methods():
        pytest.skip("requires POSIX fork for independent process SQLite test")

    registry, authority, action = _setup(tmp_path)
    grant = authority.issue(action, "exec-1", "tenant-1")
    second_registry = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite")
    second_authority = PrincipalAuthorizationAuthority(
        b"s" * 32, tmp_path / "grants.sqlite", second_registry, clock=lambda: 100
    )

    context = get_context("fork")
    start = context.Barrier(2)
    results = context.Queue()
    processes = (
        context.Process(target=_consume_grant_in_process,
                        args=(authority, action, grant, start, results, "first")),
        context.Process(target=_consume_grant_in_process,
                        args=(second_authority, action, grant, start, results, "second")),
    )
    for process in processes:
        process.start()
    try:
        outcomes = (results.get(timeout=15), results.get(timeout=15))
        for process in processes:
            process.join(timeout=15)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()

    assert sum(1 for accepted, _value in outcomes if accepted is True) == 1
    assert sum(1 for accepted, _value in outcomes if accepted is False) == 1
    assert all(process.exitcode == 0 for process in processes)

