import pytest

from core.authorization_replay import AuthorizationReplayGuard
from core.multiauth import SignedApprovalAuthority
from noryx7_runtime.engine import RuntimeEngine


def test_custom_high_risk_runtime_requires_explicit_durable_replay_guard():
    authority = SignedApprovalAuthority(required_threshold=1)
    provider = lambda _envelope, _digest: None

    with pytest.raises(ValueError, match="high_risk_actions_require_replay_guard"):
        RuntimeEngine(
            high_risk_action_types={"transfer"},
            multi_auth_authority=authority,
            authorization_provider=provider,
        )

    with pytest.raises(ValueError, match="high_risk_actions_require_durable_replay_guard"):
        RuntimeEngine(
            high_risk_action_types={"transfer"},
            multi_auth_authority=authority,
            authorization_provider=provider,
            replay_guard=AuthorizationReplayGuard(),
        )


def test_low_risk_runtime_does_not_require_replay_guard():
    engine = RuntimeEngine()
    assert engine._replay_guard is None
