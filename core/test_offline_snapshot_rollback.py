import hashlib
import json

import pytest

from core.offline import OfflineDeniedError, OfflineRuntime, OfflineSnapshot


class Cipher:
    def encrypt(self, plaintext, *, aad):
        return b"enc:" + plaintext

    def decrypt(self, ciphertext, *, aad):
        assert ciphertext.startswith(b"enc:")
        return ciphertext[4:]


class Recovery:
    def snapshot(self):
        return "normal", 1

    def run_if_normal(self, operation, *, expected_epoch=None):
        return operation()


class Policy:
    def authorize(self, *, principal_id, operation, offline):
        return True


class Verifier:
    def verify(self, result):
        return True


def make_snapshot(snapshot_id, issued_at, *, principal="p1", state_version="1"):
    body = {
        "snapshot_id": snapshot_id,
        "principal_id": principal,
        "issued_at": issued_at,
        "policy_version": "policy-1",
        "artifact_version": "artifact-1",
        "capabilities": ("compute",),
        "state_version": state_version,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return OfflineSnapshot(**body, integrity_digest=hashlib.sha256(canonical).hexdigest())


def runtime(clock=lambda: 200):
    return OfflineRuntime(
        recovery=Recovery(),
        policy=Policy(),
        verifier=Verifier(),
        cipher=Cipher(),
        clock=clock,
        snapshot_authenticator=lambda snapshot: True,
    )


def test_older_authenticated_snapshot_cannot_replace_newer_snapshot():
    rt = runtime()
    rt.install_snapshot(make_snapshot("new", 150, state_version="2"))
    with pytest.raises(OfflineDeniedError, match="snapshot_rollback"):
        rt.install_snapshot(make_snapshot("old", 149, state_version="1"))


def test_same_timestamp_different_snapshot_is_rejected():
    rt = runtime()
    rt.install_snapshot(make_snapshot("a", 150, state_version="2"))
    with pytest.raises(OfflineDeniedError, match="same_epoch_conflict"):
        rt.install_snapshot(make_snapshot("b", 150, state_version="3"))


def test_same_snapshot_timestamp_and_id_remains_idempotent():
    rt = runtime()
    snapshot = make_snapshot("a", 150, state_version="2")
    rt.install_snapshot(snapshot)
    rt.install_snapshot(snapshot)
    assert rt.state.value == "offline_ready"
