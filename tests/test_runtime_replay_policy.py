from core.multiauth import SignedApprovalAuthority
from noryx7_runtime.engine import RuntimeEngine


def test_high_risk_runtime_installs_replay_guard_when_omitted():
    engine = RuntimeEngine(
        high_risk_action_types={"transfer"},
        multi_auth_authority=SignedApprovalAuthority(required_threshold=1),
        authorization_provider=lambda _envelope, _digest: None,
    )
    assert engine._replay_guard is not None


def test_low_risk_runtime_does_not_require_replay_guard():
    engine = RuntimeEngine()
    assert engine._replay_guard is None


def test_high_risk_runtime_accepts_durable_replay_guard(tmp_path):
    from core.authorization_replay import SQLiteAuthorizationReplayGuard

    guard = SQLiteAuthorizationReplayGuard(tmp_path / "runtime-replay.db")
    engine = RuntimeEngine(
        high_risk_action_types={"transfer"},
        multi_auth_authority=SignedApprovalAuthority(required_threshold=1),
        authorization_provider=lambda _envelope, _digest: None,
        replay_guard=guard,
    )

    assert engine._replay_guard is guard
