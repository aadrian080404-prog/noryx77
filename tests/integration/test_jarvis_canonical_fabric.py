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
