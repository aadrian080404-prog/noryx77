from __future__ import annotations

import hashlib
import json

from core.system_fabric import CanonicalSystemFabric
from jarvis.core.runtime import JarvisRuntime


def test_jarvis_runtime_owns_canonical_system_fabric():
    runtime = JarvisRuntime()

    assert isinstance(runtime.system_fabric, CanonicalSystemFabric)
    assert runtime.runtime_bridge.system_fabric is runtime.system_fabric


def test_jarvis_runtime_bridge_uses_same_execution_identity_for_fabric_recording():
    runtime = JarvisRuntime()
    bridge = runtime.runtime_bridge

    assert bridge.system_fabric is runtime.system_fabric
    assert runtime.runtime_engine.runtime_id

    request_id = "jarvis-fabric-test"
    bridge.system_fabric.bind_session(
        session_id="jarvis:" + request_id,
        client_id="test-principal",
        device_id="jarvis-runtime",
        role="agent",
        capabilities=("execute",),
    )

    metadata = {"request_id": request_id}
    bridge.system_fabric.record_execution(
        execution_id=request_id,
        client_id="test-principal",
        phase="test",
        metadata=metadata,
        runtime_id=runtime.runtime_engine.runtime_id,
    )

    record = runtime.system_fabric.memory.get("execution:jarvis-fabric-test:test")
    metadata_digest = hashlib.sha256(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    expected_provenance = (
        f"NORYX7|Adrian Aristodemo|test-principal|{request_id}|test|"
        f"{runtime.runtime_engine.runtime_id}"
    ).encode("utf-8")

    assert record.payload_digest == hashlib.sha256(
        f"metadata_digest={metadata_digest}".encode("ascii")
    ).hexdigest()
    assert record.provenance_digest == hashlib.sha256(expected_provenance).hexdigest()
