import hashlib
from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.offline import OfflineSnapshot
from core.offline_snapshot_auth import (
    Ed25519OfflineSnapshotAuthenticator,
    sign_offline_snapshot,
)


def _snapshot():
    snapshot = OfflineSnapshot(
        snapshot_id="snapshot-001",
        principal_id="principal-001",
        issued_at=100,
        policy_version="policy-v1",
        artifact_version="artifact-v1",
        capabilities=("local.execute",),
        state_version="state-7",
        principal_key_fingerprint="a" * 64,
        integrity_digest="0" * 64,
    )
    return replace(
        snapshot,
        integrity_digest=hashlib.sha256(snapshot.canonical_bytes()).hexdigest(),
    )


def test_ed25519_snapshot_authenticator_accepts_trusted_issuer():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    signed = sign_offline_snapshot(
        _snapshot(), issuer_key_id="offline-issuer-v1", signing_key=private_key
    )
    verifier = Ed25519OfflineSnapshotAuthenticator(
        {"offline-issuer-v1": public_key}
    )

    assert signed.verify_integrity()
    assert verifier(signed) is True


def test_ed25519_snapshot_authenticator_rejects_modified_capability_even_with_recomputed_digest():
    private_key = Ed25519PrivateKey.generate()
    signed = sign_offline_snapshot(
        _snapshot(), issuer_key_id="offline-issuer-v1", signing_key=private_key
    )
    modified = replace(
        signed,
        capabilities=("local.execute", "admin.delete"),
        signature=signed.signature,
        integrity_digest="0" * 64,
    )
    modified = replace(
        modified,
        integrity_digest=hashlib.sha256(modified.canonical_bytes()).hexdigest(),
    )
    verifier = Ed25519OfflineSnapshotAuthenticator(
        {"offline-issuer-v1": private_key.public_key()}
    )

    assert modified.verify_integrity()
    assert verifier(modified) is False


def test_ed25519_snapshot_authenticator_rejects_unknown_or_missing_issuer_signature():
    private_key = Ed25519PrivateKey.generate()
    signed = sign_offline_snapshot(
        _snapshot(), issuer_key_id="issuer-a", signing_key=private_key
    )
    unknown_issuer = Ed25519OfflineSnapshotAuthenticator(
        {"issuer-b": Ed25519PrivateKey.generate().public_key()}
    )
    trusted = Ed25519OfflineSnapshotAuthenticator(
        {"issuer-a": private_key.public_key()}
    )
    unsigned = replace(signed, signature=b"")

    assert unknown_issuer(signed) is False
    assert trusted(unsigned) is False
