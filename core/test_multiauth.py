import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .multiauth import (
    AuthorizationProof,
    SignedApproval,
    SignedApprovalAuthority,
    SignedAuthorizationProof,
    ThresholdAuthorizer,
    sign_approval,
)


def test_high_risk_action_requires_threshold_and_current_epoch():
    auth = ThresholdAuthorizer(required_threshold=2)
    proof = AuthorizationProof("delete-root", ("a", "b"), 2, 4)
    assert auth.verify(proof, action_id="delete-root", epoch=4)
    assert not auth.verify(proof, action_id="delete-root", epoch=5)
    assert not auth.verify(proof, action_id="other", epoch=4)


def test_malformed_legacy_proof_fails_closed():
    auth = ThresholdAuthorizer(required_threshold=2)
    assert not auth.verify(object(), action_id="delete-root", epoch=4)


def test_duplicate_approvers_are_rejected():
    with pytest.raises(ValueError):
        AuthorizationProof("x", ("a", "a"), 2, 1)


def test_threshold_cannot_be_below_required_policy():
    auth = ThresholdAuthorizer(required_threshold=3)
    proof = AuthorizationProof("x", ("a", "b"), 2, 1)
    assert not auth.verify(proof, action_id="x", epoch=1)


def _authority(threshold=2):
    keys = {}
    private = {}
    for party in ("a", "b", "c"):
        key = Ed25519PrivateKey.generate()
        private[party] = key
        keys[party] = key.public_key().public_bytes_raw()
    return SignedApprovalAuthority(required_threshold=threshold, trusted_keys=keys), private


def test_signed_approvals_bind_to_exact_action_epoch_and_statement():
    auth, private = _authority()
    statement = b"canonical-action-v1"
    approvals = tuple(
        sign_approval(p, private[p], action_id="delete-root", epoch=7, action_statement=statement)
        for p in ("a", "b")
    )
    proof = SignedAuthorizationProof("delete-root", 7, statement, approvals, 2)
    assert auth.verify(proof, action_id="delete-root", epoch=7, action_statement=statement)
    assert not auth.verify(proof, action_id="delete-root", epoch=8, action_statement=statement)
    assert not auth.verify(proof, action_id="delete-root", epoch=7, action_statement=b"different")
    assert not auth.verify(proof, action_id="other", epoch=7, action_statement=statement)


def test_signed_approval_forgery_and_untrusted_key_are_rejected():
    auth, private = _authority()
    statement = b"action"
    valid = sign_approval("a", private["a"], action_id="x", epoch=1, action_statement=statement)
    forged = SignedApproval("b", private["b"].public_key().public_bytes_raw(), valid.signature)
    unknown_key = Ed25519PrivateKey.generate()
    unknown = sign_approval("z", unknown_key, action_id="x", epoch=1, action_statement=statement)
    assert not auth.verify(
        SignedAuthorizationProof("x", 1, statement, (forged, valid), 2),
        action_id="x",
        epoch=1,
        action_statement=statement,
    )
    assert not auth.verify(
        SignedAuthorizationProof("x", 1, statement, (valid, unknown), 2),
        action_id="x",
        epoch=1,
        action_statement=statement,
    )


def test_revoke_invalidates_future_authorization():
    auth, private = _authority(threshold=1)
    approval = sign_approval("a", private["a"], action_id="x", epoch=1)
    proof = SignedAuthorizationProof("x", 1, b"", (approval,), 1)
    assert auth.verify(proof, action_id="x", epoch=1)
    auth.revoke("a")
    assert not auth.verify(proof, action_id="x", epoch=1)


def test_signed_proof_rejects_duplicate_approver_ids():
    auth, private = _authority()
    approval = sign_approval("a", private["a"], action_id="x", epoch=1)
    with pytest.raises(ValueError):
        SignedAuthorizationProof("x", 1, b"", (approval, approval), 2)
