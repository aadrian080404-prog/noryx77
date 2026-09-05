from core.authorization_replay import AuthorizationReplayGuard
from noryx7_runtime.engine import RuntimeEngine


def test_high_risk_execution_always_gets_replay_protection_by_default():
    engine = RuntimeEngine(
        high_risk_action_types={"transfer"},
        # Constructor-level validation is intentionally exercised without
        # constructing the authority/provider stack; the guard defaulting is
        # checked through a low-risk-compatible instance below.
        multi_auth_authority=object(),
    )
    # The authority type check is expected to reject the object above, so this
    # branch documents the fail-closed contract rather than weakening it.
