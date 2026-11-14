import pytest

from core.adversarial_game import (
    AbstractSecurityState,
    AttackerMove,
    BoundedAdversarialGame,
    DefenderMove,
)


def test_game_is_deterministic_and_bounded():
    engine = BoundedAdversarialGame()
    state = AbstractSecurityState(credential_compromised=True, replay_protected=False)
    first = engine.solve(state, horizon=3)
    second = engine.solve(state, horizon=3)
    assert first == second
    assert isinstance(first.first_defense, DefenderMove)
    assert first.horizon == 3
    assert first.evaluated_states > 0
    assert first.evaluated_states < 10_000


def test_replay_guard_prevents_abstract_replay_compromise():
    state = AbstractSecurityState(replay_protected=True)
    result = BoundedAdversarialGame._attack(state, AttackerMove.REPLAY)
    assert result.credential_compromised is False
    assert result.replay_protected is True


def test_credential_revocation_prevents_following_exfiltration():
    state = AbstractSecurityState(credential_compromised=True)
    revoked = BoundedAdversarialGame._defend(state, DefenderMove.REVOKE_CREDENTIAL)
    result = BoundedAdversarialGame._attack(revoked, AttackerMove.EXFILTRATE)
    assert result.data_exposed is False


def test_evidence_reconstruction_requires_valid_checkpoint():
    invalid = AbstractSecurityState(evidence_integrity=False, checkpoint_valid=False)
    result = BoundedAdversarialGame._defend(invalid, DefenderMove.VERIFY_EVIDENCE)
    assert result.evidence_integrity is False
    valid = AbstractSecurityState(evidence_integrity=False, checkpoint_valid=True)
    repaired = BoundedAdversarialGame._defend(valid, DefenderMove.VERIFY_EVIDENCE)
    assert repaired.evidence_integrity is True


def test_isolation_blocks_exfiltration_but_reduces_availability():
    state = AbstractSecurityState(credential_compromised=True)
    isolated = BoundedAdversarialGame._defend(state, DefenderMove.ISOLATE)
    result = BoundedAdversarialGame._attack(isolated, AttackerMove.EXFILTRATE)
    assert result.data_exposed is False
    assert result.service_available is False


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5, 9])
def test_invalid_horizon_is_rejected(horizon):
    with pytest.raises(ValueError, match="invalid_game_horizon"):
        BoundedAdversarialGame().solve(AbstractSecurityState(), horizon=horizon)


@pytest.mark.parametrize("field", [
    "credential_compromised", "replay_protected", "evidence_integrity",
    "data_exposed", "service_available", "isolated", "checkpoint_valid",
])
def test_security_state_rejects_non_boolean_flags(field):
    with pytest.raises(TypeError, match=f"{field}_must_be_bool"):
        AbstractSecurityState(**{field: 1})


def test_game_rejects_untyped_state():
    with pytest.raises(TypeError, match="abstract_security_state_required"):
        BoundedAdversarialGame().solve(object())
