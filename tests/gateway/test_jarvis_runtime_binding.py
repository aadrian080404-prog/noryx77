from __future__ import annotations

import pytest

from core.actions import AuthorizationAuthority
from core.identity import AgentIdentityAuthority
from core.operational_runtime import OperationalNORYXRuntime
from core.tools import ToolExecutor
from jarvis.core.policy import Policy
from noryx7_runtime.engine import RuntimeEngine


def _runtime_shell() -> OperationalNORYXRuntime:
    runtime = object.__new__(OperationalNORYXRuntime)
    runtime.tool_executor = object.__new__(ToolExecutor)
    runtime.audit = type("Audit", (), {"record": lambda self, *args, **kwargs: None})()
    runtime._jarvis_bridge = None
    return runtime


def test_operational_runtime_binds_jarvis_bridge_to_canonical_controls():
    runtime = _runtime_shell()
    principal, _ = AgentIdentityAuthority.generate("jarvis-test")
    runtime_engine = RuntimeEngine()
    authorization = AuthorizationAuthority(b"noryx7-jarvis-test-secret-32-bytes!!")
    policy = Policy()

    bridge = runtime.configure_jarvis_bridge(
        runtime_engine=runtime_engine,
        authorization=authorization,
        principal=principal,
        policy=policy,
    )

    assert runtime.jarvis_bridge is bridge
    assert bridge.runtime_engine is runtime_engine
    assert bridge.tool_executor is runtime.tool_executor
    assert bridge.authorization is authorization
    assert bridge.principal is principal
    assert bridge.policy is policy


def test_operational_runtime_keeps_jarvis_fail_closed_until_bound():
    runtime = _runtime_shell()
    with pytest.raises(RuntimeError, match="jarvis_bridge_not_configured"):
        runtime.execute_jarvis(object(), object())
