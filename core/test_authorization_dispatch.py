import threading

from core.actions import AuthorizationAuthority
from core.authorization_replay import AuthenticatedAuthorizationReplayGuard
from core.contracts import ActionSpec
from core.identity import AgentIdentityAuthority, IdentityRegistry


def test_authorized_dispatch_does_not_hold_identity_registry_lock(tmp_path):
    registry = IdentityRegistry()
    identity, _ = AgentIdentityAuthority.generate("dispatch-agent")
    registry.register(identity)
    replay = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="test-key",
        path=str(tmp_path / "replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay,
        require_authenticated_replay=True,
    )
    action = ActionSpec(
        "action-1",
        "system_change",
        target="test-target",
        risk_class="high",
        requires_authorization=True,
        execution_id="execution-1",
    )
    grant = authority.issue(action, "execution-1", principal=identity)
    revoked = threading.Event()

    def executor():
        worker = threading.Thread(
            target=lambda: (registry.revoke(identity.agent_id), revoked.set()),
            daemon=True,
        )
        worker.start()
        worker.join(timeout=1.0)
        return not worker.is_alive()

    try:
        consumed, dispatched = authority.consume_and_execute(
            action, "execution-1", grant, identity, executor
        )
        assert consumed
        assert dispatched is True
        assert revoked.is_set()
    finally:
        replay.close()
