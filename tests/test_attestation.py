import hashlib
import pytest

from core.attestation import Attestation, AttestationVerifier, RuntimeIdentity


class AcceptingVerifier(AttestationVerifier):
    def verify(self, attestation):
        return True


class RejectingVerifier(AttestationVerifier):
    def verify(self, attestation):
        return False


def test_runtime_identity_requires_valid_external_attestation():
    identity = RuntimeIdentity(verifier=AcceptingVerifier(), clock=lambda: 100)
    attestation = Attestation("runtime-a", hashlib.sha256(b"measurement").hexdigest(), 90, 110, "nonce-a")
    identity.bind(attestation)
    assert identity.is_bound()
    assert identity.runtime_id == "runtime-a"
    assert len(identity.binding_digest()) == 64


def test_rejected_attestation_fails_closed():
    identity = RuntimeIdentity(verifier=RejectingVerifier(), clock=lambda: 100)
    attestation = Attestation("runtime-a", hashlib.sha256(b"measurement").hexdigest(), 90, 110, "nonce-a")
    with pytest.raises(PermissionError, match="attestation_verification_failed"):
        identity.bind(attestation)
