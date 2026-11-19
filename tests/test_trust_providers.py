import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.identity import AgentIdentity
from core.trust_providers import (
    advance_witness_epoch, require_witness_epoch, sign_for_identity,
)


class FakeKeyProvider:
    def __init__(self, key):
        self.key = key

    def public_key(self, key_id):
        return self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def sign(self, key_id, message):
        return self.key.sign(message)


class FakeWitness:
    def __init__(self, epoch=0):
        self.epoch = epoch

    def read_epoch(self, namespace):
        return self.epoch

    def advance_epoch(self, namespace, expected_epoch, next_epoch):
        if self.epoch != expected_epoch or next_epoch != expected_epoch + 1:
            return False
        self.epoch = next_epoch
        return True


def _identity(key):
    return AgentIdentity("provider-agent", key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ))


def test_key_provider_signs_only_for_matching_identity():
    key = Ed25519PrivateKey.generate()
    identity = _identity(key)
    signature = sign_for_identity(
        FakeKeyProvider(key), key_id="kms://agent/key-1",
        identity=identity, message=b"noryx7-test",
    )
    key.public_key().verify(signature, b"noryx7-test")


def test_key_provider_rejects_wrong_identity_key():
    provider_key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    with pytest.raises(PermissionError, match="signing_key_identity_mismatch"):
        sign_for_identity(
            FakeKeyProvider(provider_key), key_id="key-1",
            identity=_identity(other_key), message=b"payload",
        )


def test_key_provider_fails_closed_when_unavailable():
    class Broken:
        def public_key(self, key_id):
            raise OSError("offline")
        def sign(self, key_id, message):
            raise AssertionError("must not sign")
    key = Ed25519PrivateKey.generate()
    with pytest.raises(PermissionError, match="signing_key_unavailable"):
        sign_for_identity(Broken(), key_id="key-1", identity=_identity(key), message=b"x")


def test_external_witness_requires_exact_epoch_match():
    witness = FakeWitness(4)
    assert require_witness_epoch(witness, namespace="agent/a", local_epoch=4) == 4
    with pytest.raises(PermissionError, match="monotonic_epoch_mismatch"):
        require_witness_epoch(witness, namespace="agent/a", local_epoch=3)


def test_external_witness_advances_with_compare_and_swap():
    witness = FakeWitness(7)
    assert advance_witness_epoch(
        witness, namespace="agent/a", expected_epoch=7, next_epoch=8
    ) == 8
    with pytest.raises(PermissionError, match="monotonic_witness_conflict"):
        advance_witness_epoch(
            witness, namespace="agent/a", expected_epoch=7, next_epoch=8
        )


@pytest.mark.parametrize("expected,next_epoch", [(0, 0), (1, 3), (True, 2), (-1, 0)])
def test_external_witness_rejects_invalid_transitions(expected, next_epoch):
    with pytest.raises(ValueError):
        advance_witness_epoch(
            FakeWitness(expected if isinstance(expected, int) and not isinstance(expected, bool) else 0),
            namespace="agent/a", expected_epoch=expected, next_epoch=next_epoch,
        )
