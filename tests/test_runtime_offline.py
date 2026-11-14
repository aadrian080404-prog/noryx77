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
    )
    return runtime


def test_runtime_offline_uses_shared_policy_verification_recovery_and_state():
    runtime = _runtime()
    runtime.install_offline_snapshot(_snapshot("exec-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(task, capability="compute_local", local_executor=lambda task: "local-result")

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
    runtime.install_offline_snapshot(_snapshot("exec-1"))
    task = TaskSpec("task-1", "local-analysis", "analyze", {"x": 1}, execution_id="exec-1")

    result = runtime.run_offline(task, capability="compute_local", local_executor=lambda task: object())

    assert result["status"] == "rejected"
    assert len(runtime.state) == 0
    assert len(runtime.offline.queue) == 0
