import pytest

from .multiauth import AuthorizationProof, ThresholdAuthorizer


def test_high_risk_action_requires_threshold_and_current_epoch():
    auth = ThresholdAuthorizer(required_threshold=2)
    proof = AuthorizationProof("delete-root", ("a", "b"), 2, 4)
    assert auth.verify(proof, action_id="delete-root", epoch=4)
    assert not auth.verify(proof, action_id="delete-root", epoch=5)
    assert not auth.verify(proof, action_id="other", epoch=4)


def test_duplicate_approvers_are_rejected():
    with pytest.raises(ValueError):
        AuthorizationProof("x", ("a", "a"), 2, 1)


def test_threshold_cannot_be_below_required_policy():
    auth = ThresholdAuthorizer(required_threshold=3)
    proof = AuthorizationProof("x", ("a", "b"), 2, 1)
    assert not auth.verify(proof, action_id="x", epoch=1)
