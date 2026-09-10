from __future__ import annotations

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

    bridge.system_fabric.record_execution(
        execution_id=request_id,
        client_id="test-principal",
        phase="test",
        metadata={"request_id": request_id},
    )

    record_ids = {
        record.record_id
        for record in runtime.system_fabric.memory.snapshot()
    }
    assert "execution:jarvis-fabric-test:test" in record_ids
