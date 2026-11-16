import hashlib
import json

from core.contracts import TaskSpec
from core.crypto import AuthenticatedCipher, InMemoryKeyProvider
from core.offline import OfflineSnapshot
from core.runtime import NORYXRuntime


def _snapshot(principal: str, issued_at: int = 100) -> OfflineSnapshot:
    body = {
        "snapshot_id": "snap-1",
        "principal_id": principal,
        "issued_at": issued_at,
        "policy_version": "policy-1",
        "artifact_version": "artifact-1",
        "capabilities": ("compute_local",),
        "state_version": "0",
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return OfflineSnapshot(**body, integrity_digest=hashlib.sha256(canonical).hexdigest())


def _runtime() -> NORYXRuntime:
    runtime = NORYXRuntime()
    provider = InMemoryKeyProvider({"offline-1": b"K" * 32})
    runtime.configure_offline(
        cipher=AuthenticatedCipher(provider),
        key_id="offline-1",
        snapshot_authenticator=lambda snapshot: snapshot.snapshot_id == "snap-1",
        clock=lambda: 100,
        principal_authenticator=lambda principal_id, fingerprint: (
            principal_id == "user-1" and fingerprint == "a" * 64
        ),
    )
    return runtime


def test_runtime_offline_uses_shared_policy_verification_recovery_and_state():
    runtime = _runtime()
    runtime.install_offline_snapshot(_snapshot("user-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(task, capability="compute_local", local_executor=lambda task: "local-result", principal_id="user-1", principal_key_fingerprint="a" * 64)

    assert result["status"] == "completed"
    assert result["state_commit"].verification_stage == "runtime_result"
    assert result["state_commit"].state.status == "committed"
    assert result["sync_envelope"].ciphertext != b""
    assert runtime.offline is not None
    assert runtime.offline.state.value == "sync_pending"


def test_runtime_offline_rejects_unconfigured_execution():
    runtime = NORYXRuntime()
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(task, capability="compute_local", local_executor=lambda task: "ok")

    assert result["status"] == "rejected"
    assert result["reason"] == "offline_not_configured"


def test_runtime_offline_does_not_commit_unverified_result():
    runtime = _runtime()
    runtime.install_offline_snapshot(_snapshot("user-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(task, capability="compute_local", local_executor=lambda task: object(), principal_id="user-1", principal_key_fingerprint="a" * 64)

    assert result["status"] == "rejected"
    assert len(runtime.state) == 0
    assert len(runtime.offline.queue) == 0


def test_runtime_offline_rejects_missing_verified_principal_before_execution():
    runtime = _runtime()
    runtime.install_offline_snapshot(_snapshot("user-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")
    called = []

    result = runtime.run_offline(
        task, capability="compute_local",
        local_executor=lambda task: called.append(True) or "should-not-run",
    )

    assert result["status"] == "rejected"
    assert result["reason"] == "verified_offline_principal_required"
    assert called == []
    assert len(runtime.state) == 0


def test_runtime_offline_rejects_snapshot_bound_to_another_principal():
    runtime = _runtime()
    runtime.install_offline_snapshot(_snapshot("different-user"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(
        task, capability="compute_local",
        local_executor=lambda task: "should-not-run",
        principal_id="user-1", principal_key_fingerprint="a" * 64,
    )

    assert result["status"] == "rejected"
    assert result["reason"] == "offline_snapshot_principal_mismatch"
    assert len(runtime.state) == 0


def test_runtime_offline_rejects_authenticator_that_does_not_return_true():
    runtime = _runtime()
    runtime._offline_principal_authenticator = lambda *_: 1
    runtime.install_offline_snapshot(_snapshot("user-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(
        task, capability="compute_local",
        local_executor=lambda task: "should-not-run",
        principal_id="user-1", principal_key_fingerprint="a" * 64,
    )

    assert result["status"] == "rejected"
    assert result["reason"] == "offline_principal_authentication_failed"
    assert len(runtime.state) == 0
