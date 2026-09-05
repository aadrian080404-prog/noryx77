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
