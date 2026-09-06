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

    assert not auth.verify(SignedAuthorizationProof("x", 1, statement, (forged, valid), 2), action_id="x", epoch=1, action_statement=statement)
    assert not auth.verify(SignedAuthorizationProof("x", 1, statement, (valid, unknown), 2), action_id="x", epoch=1, action_statement=statement)


def test_revoke_invalidates_future_authorization():
    auth, private = _authority(threshold=1)
    approval = sign_approval("a", private["a"], action_id="x", epoch=1)
    proof = SignedAuthorizationProof("x", 1, b"", (approval,), 1)
    assert auth.verify(proof, action_id="x", epoch=1)
    auth.revoke("a")
    assert not auth.verify(proof, action_id="x", epoch=1)

