import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.supply_chain import ArtifactManifest, SupplyChainVerifier, manifest_digest


def _manifest(private_key, artifact: bytes) -> ArtifactManifest:
    public_key = private_key.public_key().public_bytes_raw()
    digest = hashlib.sha256(artifact).hexdigest()
    signature = private_key.sign(manifest_digest("core", "1", digest))
    return ArtifactManifest("core", "1", digest, public_key, signature)


def test_strict_verification_binds_signature_to_actual_artifact():
    private_key = Ed25519PrivateKey.generate()
    artifact = b"trusted artifact"
    manifest = _manifest(private_key, artifact)
    verifier = SupplyChainVerifier({manifest.signer_key})

    assert verifier.verify(manifest)
    assert verifier.verify_artifact(manifest, artifact)
    assert not verifier.verify_artifact(manifest, b"substituted artifact")


def test_artifact_digest_must_be_lowercase_hex():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes_raw()
    with pytest.raises(ValueError, match="invalid_artifact_digest"):
        ArtifactManifest("core", "1", "A" * 64, public_key, b"x" * 64)
