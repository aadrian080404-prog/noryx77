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
