from core.actions import AuthorizationAuthority
from core.authorization_replay import AuthenticatedAuthorizationReplayGuard
from core.contracts import ActionSpec
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.runtime import NORYXRuntime


class StubSandboxAdapter:
    environment = "sandboxed_process"

    def execute(self, action):
        return {"status": "executed"}


def test_canonical_runtime_exposes_explicit_sandbox_adapter():
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(sandboxed_process_adapter=adapter)

    assert runtime.hypersynth.sandboxed_process_adapter is adapter
    assert runtime.capability_registry.resolve("sandboxed_process") is not None
    assert runtime.capability_registry.risk("sandboxed_process") == "high"


def test_canonical_runtime_keeps_process_capability_disabled_by_default():
    runtime = NORYXRuntime()
    assert runtime.capability_registry.resolve("sandboxed_process") is None


def test_canonical_runtime_binds_collaboration_to_identity_registry():
    runtime = NORYXRuntime()
    assert runtime.hypersynth.collaboration.identity_registry is runtime.identity_registry



def test_canonical_runtime_accepts_only_durable_authenticated_registry_bound_authority(tmp_path):
    registry = IdentityRegistry()
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-test-key",
        path=str(tmp_path / "authorization-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )

    runtime = NORYXRuntime(identity_registry=registry, authorization_authority=authority)

    assert runtime.identity_registry is registry
    assert runtime.action_gate.authorization is authority
    assert runtime.hypersynth.action_gate.authorization is authority
    replay_guard.close()


def test_canonical_runtime_rejects_ephemeral_authority(tmp_path):
    import pytest

    registry = IdentityRegistry()
    authority = AuthorizationAuthority(b"a" * 32, identity_registry=registry)
    with pytest.raises(ValueError, match="invalid_runtime_authorization_authority"):
        NORYXRuntime(identity_registry=registry, authorization_authority=authority)


def test_canonical_runtime_rejects_authority_bound_to_another_registry(tmp_path):
    import pytest

    registry = IdentityRegistry()
    other_registry = IdentityRegistry()
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-test-key",
        path=str(tmp_path / "other-authorization-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=other_registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    with pytest.raises(ValueError, match="invalid_runtime_authorization_authority"):
        NORYXRuntime(identity_registry=registry, authorization_authority=authority)
    replay_guard.close()



def test_canonical_runtime_keeps_high_risk_process_action_fail_closed_without_authority():
    runtime = NORYXRuntime(sandboxed_process_adapter=StubSandboxAdapter())
    action = ActionSpec(
        action_id="sandbox-action",
        action_type="sandboxed_process",
        target="workspace",
        parameters={"action_id": "sandbox-action", "argv": ["/usr/bin/true"]},
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-no-authority",
    )
    output, decision = runtime.tool_executor.execute(
        action,
        execution_id="exec-no-authority",
    )
    assert output is None
    assert not decision.valid
    assert decision.reason == "authorization_required"
    assert adapter.actions == []

def test_canonical_runtime_dispatches_authorized_sandbox_action_once(tmp_path):
    registry = IdentityRegistry()
    principal, _private_key = AgentIdentityAuthority.generate("sandbox-operator")
    registry.register(principal)
    replay_guard = AuthenticatedAuthorizationReplayGuard(
        integrity_key=b"r" * 32,
        key_id="runtime-dispatch-test-key",
        path=str(tmp_path / "dispatch-replay.sqlite3"),
    )
    authority = AuthorizationAuthority(
        b"a" * 32,
        identity_registry=registry,
        replay_guard=replay_guard,
        require_authenticated_replay=True,
    )
    adapter = StubSandboxAdapter()
    runtime = NORYXRuntime(
        identity_registry=registry,
        authorization_authority=authority,
        sandboxed_process_adapter=adapter,
    )
    action = ActionSpec(
        action_id="sandbox-authorized-once",
        action_type="sandboxed_process",
        target="workspace",
        parameters={"action_id": "sandbox-authorized-once", "argv": ["/usr/bin/true"]},
        risk_class="high",
        requires_authorization=True,
        execution_id="exec-sandbox-authorized-once",
    )
    grant = authority.issue(
        action,
        "exec-sandbox-authorized-once",
        principal=principal,
    )
    try:
        output, check = runtime.tool_executor.execute(
            action,
            execution_id="exec-sandbox-authorized-once",
            grant=grant,
            principal=principal,
        )
        assert check.valid
        assert output == {"status": "executed"}
        assert len(adapter.actions) == 1

        replay_output, replay_check = runtime.tool_executor.execute(
            action,
            execution_id="exec-sandbox-authorized-once",
            grant=grant,
            principal=principal,
        )
        assert replay_output is None
        assert not replay_check.valid
        assert replay_check.reason == "invalid_authorization_grant"
        assert len(adapter.actions) == 1
    finally:
        replay_guard.close()
