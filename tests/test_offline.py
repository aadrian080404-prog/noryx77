from dataclasses import replace
from hashlib import sha256

import pytest

from core.offline import (
    OfflineConflictError,
    OfflineDeniedError,
    OfflineExecution,
    OfflineRuntime,
    OfflineSnapshot,
)


class Recovery:
    def __init__(self):
        self.state = "normal"
        self.epoch = 7

    def snapshot(self):
        return self.state, self.epoch

    def run_if_normal(self, operation, expected_epoch=None):
        if self.state != "normal" or expected_epoch != self.epoch:
            raise OfflineDeniedError("recovery_gate")
        return operation()


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def authorize(self, *, principal_id, operation, offline):
        return self.allowed and offline


class Verifier:
    def __init__(self, valid=True):
        self.valid = valid

    def verify(self, result):
        return self.valid


class Cipher:
    def encrypt(self, plaintext, *, aad):
        return b"ENC:" + aad + b":" + plaintext

    def decrypt(self, ciphertext, *, aad):
        prefix = b"ENC:" + aad + b":"
        if not ciphertext.startswith(prefix):
            raise ValueError("bad_ciphertext")
        return ciphertext[len(prefix):]


def make_snapshot(now=100, snapshot_id="snap-1", state_version="state-1"):
    base = OfflineSnapshot(snapshot_id, "principal-1", now, "policy-1", "artifact-1", ("local.execute",), state_version, "0" * 64)
    return replace(base, integrity_digest=sha256(base.canonical_bytes()).hexdigest())


def make_runtime(recovery=None, policy=None, verifier=None, now=100, max_snapshot_age=86_400, authenticator=None):
    return OfflineRuntime(
        recovery=recovery or Recovery(),
        policy=policy or Policy(),
        verifier=verifier or Verifier(),
        cipher=Cipher(),
        clock=lambda: now,
        snapshot_authenticator=authenticator or (lambda snapshot: snapshot.snapshot_id in {"snap-1", "snap-2"}),
        max_snapshot_age=max_snapshot_age,
    )


def make_execution(payload=b"approved"):
    return OfflineExecution("exec-1", "principal-1", "local-op", "local.execute", sha256(payload).hexdigest(), "state-1")


def test_offline_executes_approved_local_task_and_queues_encrypted_sync():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    payload = b"approved"
    committed = []
    envelope = runtime.execute(execution=make_execution(payload), payload=payload, result={"ok": True}, commit=lambda e, r: committed.append(r))
    assert committed == [{"ok": True}]
    assert envelope.ciphertext != payload
    assert runtime.queue.decrypt("exec-1") == payload
    assert runtime.state.value == "sync_pending"


def test_cloud_only_capability_is_denied_offline():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    execution = replace(make_execution(), capability="cloud.execute")
    with pytest.raises(OfflineDeniedError, match="capability"):
        runtime.execute(execution=execution, payload=b"approved", result=True, commit=lambda *_: None)


def test_stale_or_tampered_snapshot_fails_closed():
    runtime = make_runtime(now=100, max_snapshot_age=10)
    stale = make_snapshot(now=0)
    with pytest.raises(OfflineDeniedError, match="stale"):
        runtime.install_snapshot(stale)

    runtime = make_runtime()
    tampered = replace(make_snapshot(), artifact_version="attacker")
    with pytest.raises(OfflineDeniedError, match="invalid"):
        runtime.install_snapshot(tampered)


def test_recovery_state_blocks_offline_execution_before_commit():
    recovery = Recovery()
    recovery.state = "lockdown"
    runtime = make_runtime(recovery=recovery)
    runtime.install_snapshot(make_snapshot())
    with pytest.raises(OfflineDeniedError, match="recovery"):
        runtime.execute(execution=make_execution(), payload=b"approved", result=True, commit=lambda *_: pytest.fail("commit bypassed"))


def test_unverified_result_cannot_commit_offline():
    runtime = make_runtime(verifier=Verifier(valid=False))
    runtime.install_snapshot(make_snapshot())
    with pytest.raises(OfflineDeniedError, match="unverified"):
        runtime.execute(execution=make_execution(), payload=b"approved", result=True, commit=lambda *_: pytest.fail("commit bypassed"))


def test_duplicate_enqueue_is_idempotent_and_queue_is_bounded():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    payload = b"approved"
    first = runtime.execute(execution=make_execution(payload), payload=payload, result=True, commit=lambda *_: None)
    second = runtime.queue.enqueue(make_execution(payload), payload)
    assert first.sequence == second.sequence
    assert len(runtime.queue) == 1


def test_reconnect_requires_authentication_and_verified_channel():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    with pytest.raises(OfflineDeniedError, match="reconnect"):
        runtime.reconnect(authenticated=False, channel_verified=True)
    with pytest.raises(OfflineDeniedError, match="reconnect"):
        runtime.reconnect(authenticated=True, channel_verified=False)


def test_conflicting_remote_version_never_silently_overwrites():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    runtime.execute(execution=make_execution(), payload=b"approved", result=True, commit=lambda *_: None)
    runtime.reconnect(authenticated=True, channel_verified=True)
    with pytest.raises(OfflineConflictError, match="conflict"):
        runtime.acknowledge_synced("exec-1", remote_state_version="different-state")
    assert len(runtime.queue) == 1


def test_older_authenticated_snapshot_cannot_rollback_newer_snapshot():
    runtime = make_runtime(now=200)
    runtime.install_snapshot(make_snapshot(now=200, snapshot_id="snap-2", state_version="state-2"))
    with pytest.raises(OfflineDeniedError, match="rollback"):
        runtime.install_snapshot(make_snapshot(now=150, snapshot_id="snap-1", state_version="state-1"))


def test_distinct_snapshot_with_same_issuance_epoch_cannot_replace_current_one():
    runtime = make_runtime(now=200)
    runtime.install_snapshot(make_snapshot(now=200, snapshot_id="snap-1", state_version="state-1"))
    with pytest.raises(OfflineDeniedError, match="same_epoch"):
        runtime.install_snapshot(make_snapshot(now=200, snapshot_id="snap-2", state_version="state-2"))


def test_duplicate_execution_identity_cannot_change_payload_or_principal():
    runtime = make_runtime()
    runtime.install_snapshot(make_snapshot())
    payload = b"approved"
    execution = make_execution(payload)
    runtime.queue.enqueue(execution, payload)
    altered = replace(execution, principal_id="principal-2")
    with pytest.raises(OfflineConflictError, match="identity_conflict"):
        runtime.queue.enqueue(altered, payload)
