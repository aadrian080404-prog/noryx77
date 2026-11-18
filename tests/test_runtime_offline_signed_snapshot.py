import hashlib
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.crypto import AuthenticatedCipher, InMemoryKeyProvider
from core.offline import OfflineDeniedError, OfflineSnapshot, SQLiteOfflineSyncQueue
from core.offline_adapters import BoundAuthenticatedCipher
from core.offline_snapshot_auth import (
    Ed25519OfflineSnapshotAuthenticator,
    sign_offline_snapshot,
)
from core.runtime import NORYXRuntime


class _Anchor:
    def accept(self, issued_at, snapshot_id):
        return True


def _snapshot():
    unsigned = OfflineSnapshot(
        snapshot_id="signed-runtime-snapshot",
        principal_id="principal-verified",
        issued_at=100,
        policy_version="policy-v3",
        artifact_version="artifact-v2",
        capabilities=("local.execute",),
        state_version="state-9",
        principal_key_fingerprint="d" * 64,
        integrity_digest="0" * 64,
    )
    return replace(
        unsigned,
        integrity_digest=hashlib.sha256(unsigned.canonical_bytes()).hexdigest(),
    )


def _runtime(tmp_path, authenticator):
    provider = InMemoryKeyProvider({"offline-key": b"o" * 32})
    cipher = AuthenticatedCipher(provider)
    queue = SQLiteOfflineSyncQueue(
        str(tmp_path / "signed-offline.sqlite3"),
        BoundAuthenticatedCipher(cipher, key_id="offline-key"),
    )
    runtime = NORYXRuntime()
    runtime.configure_offline(
        cipher=cipher,
        key_id="offline-key",
        snapshot_authenticator=authenticator,
        clock=lambda: 100,
        offline_queue=queue,
        monotonic_anchor=_Anchor(),
    )
    return runtime, queue


def test_canonical_runtime_requires_ed25519_signed_offline_snapshot(tmp_path):
    issuer = Ed25519PrivateKey.generate()
    authenticator = Ed25519OfflineSnapshotAuthenticator(
        {"noryx7-offline-issuer-v1": issuer.public_key()}
    )
    runtime, queue = _runtime(tmp_path, authenticator)
    signed = sign_offline_snapshot(
        _snapshot(),
        issuer_key_id="noryx7-offline-issuer-v1",
        signing_key=issuer,
    )
    tampered = replace(
        signed,
        capabilities=("local.execute", "admin.delete"),
        integrity_digest="0" * 64,
    )
    tampered = replace(
        tampered,
        integrity_digest=hashlib.sha256(tampered.canonical_bytes()).hexdigest(),
    )

    try:
        with pytest.raises(OfflineDeniedError, match="invalid_offline_snapshot"):
            runtime.install_offline_snapshot(_snapshot())
        with pytest.raises(OfflineDeniedError, match="invalid_offline_snapshot"):
            runtime.install_offline_snapshot(tampered)

        runtime.install_offline_snapshot(signed)
        assert runtime.offline is not None
        assert runtime.offline.state.value == "offline_ready"
    finally:
        queue.close()
