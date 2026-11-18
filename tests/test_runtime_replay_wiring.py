import pytest

from core.actions import ActionSpec
from core.authorization_replay import SQLiteAuthorizationReplayGuard
from core.identity import AgentIdentityAuthority
from core.runtime import NORYXRuntime


def test_runtime_wires_durable_replay_authority_to_both_action_gates(tmp_path):
    replay = SQLiteAuthorizationReplayGuard(tmp_path / "runtime-replay.sqlite3", max_tokens=16)
    runtime = NORYXRuntime(
        authorization_secret=b"R" * 32,
        replay_guard=replay,
    )

    assert runtime.authorization is not None
    assert runtime.authorization._identity_registry is runtime.identity_registry
    assert runtime.authorization._replay_guard is replay
    assert runtime.action_gate.authorization is runtime.authorization
    assert runtime.hypersynth.action_gate.authorization is runtime.authorization

    principal, _private_key = AgentIdentityAuthority.generate("runtime-test-principal")
    runtime.identity_registry.register(principal)
    action = ActionSpec(
        action_id="runtime-authorized-action",
        action_type="write",
        target="local-resource",
        parameters={"value": 1},
        risk_class="normal",
        requires_authorization=True,
        execution_id="runtime-execution",
    )
    grant = runtime.authorization.issue(
        action, "runtime-execution", principal=principal
    )
    assert runtime.authorization.consume(
        action, "runtime-execution", grant, principal=principal
    )


def test_runtime_preserves_legacy_no_authorization_default():
    runtime = NORYXRuntime()
    assert runtime.authorization is None
    assert runtime.action_gate.authorization is None
    assert runtime.hypersynth.action_gate.authorization is None


def test_runtime_requires_authorization_secret_when_replay_guard_is_supplied(tmp_path):
    replay = SQLiteAuthorizationReplayGuard(tmp_path / "orphan-replay.sqlite3")
    with pytest.raises(ValueError, match="authorization_secret_required_for_replay_guard"):
        NORYXRuntime(replay_guard=replay)
