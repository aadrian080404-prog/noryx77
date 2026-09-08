import hashlib

import pytest

from core.crypto import AuthenticatedCipher, InMemoryKeyProvider, KEY_SIZE
from core.offline import OfflineSnapshot
from jarvis.core.contracts import ActionResult, Plan, PlanStep, Request
from jarvis.core.runtime import JarvisRuntime


def _snapshot(principal: str, now: int = 100):
    body = {
        "snapshot_id": "snap-1",
        "principal_id": principal,
        "issued_at": now,
        "policy_version": "p1",
        "artifact_version": "a1",
        "capabilities": ("jarvis.execute",),
        "state_version": "s1",
    }
    import json
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return OfflineSnapshot(integrity_digest=digest, **body)


def test_jarvis_offline_requires_explicit_configuration():
    runtime = JarvisRuntime()
    request = Request("do local", "principal-1", "req-1")
    plan = Plan("req-1", (PlanStep("s1", "compute", "local", {}),))
    with pytest.raises(RuntimeError, match="offline_runtime_not_configured"):
        runtime.execute_offline(request=request, plan=plan, snapshot_state_version="s1", local_execute=lambda _: ActionResult("s1", True, "ok"))


def test_jarvis_offline_binds_snapshot_identity_and_commits_verified_result():
    runtime = JarvisRuntime()
    provider = InMemoryKeyProvider({"offline": b"K" * KEY_SIZE})
    cipher = AuthenticatedCipher(provider)
    binding = runtime.configure_offline(cipher=__import__('core.offline_adapters', fromlist=['BoundAuthenticatedCipher']).BoundAuthenticatedCipher(cipher, key_id="offline"), clock=lambda: 100, snapshot_authenticator=lambda snap: snap.principal_id == "principal-1")
    binding.install_snapshot(_snapshot("principal-1"))
    request = Request("do local", "principal-1", "req-2")
    plan = Plan("req-2", (PlanStep("s1", "compute", "local", {}),))
    result = runtime.execute_offline(request=request, plan=plan, snapshot_state_version="s1", local_execute=lambda _: ActionResult("s1", True, "ok"))
    assert result.execution.execution_id == "req-2"
    assert runtime.state.get("req-2") is not None


def test_jarvis_offline_rejects_wrong_snapshot_identity_before_local_execution():
    runtime = JarvisRuntime()
    provider = InMemoryKeyProvider({"offline": b"K" * KEY_SIZE})
    cipher = AuthenticatedCipher(provider)
    binding = runtime.configure_offline(cipher=__import__('core.offline_adapters', fromlist=['BoundAuthenticatedCipher']).BoundAuthenticatedCipher(cipher, key_id="offline"), clock=lambda: 100, snapshot_authenticator=lambda snap: True)
    binding.install_snapshot(_snapshot("principal-1"))
    request = Request("do local", "principal-2", "req-3")
    plan = Plan("req-3", (PlanStep("s1", "compute", "local", {}),))
    called = False
    def local(_):
        nonlocal called
        called = True
        return ActionResult("s1", True, "ok")
    with pytest.raises(Exception, match="offline_identity_mismatch"):
        runtime.execute_offline(request=request, plan=plan, snapshot_state_version="s1", local_execute=local)
    assert called is False
