import pytest

from core.identity import AgentIdentityAuthority
from core.llm.model_fabric_bridge import ModelFabricBridge
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.model_fabric import ModelFabric


class FakeModel:
    name = "auth-test"
    capabilities = frozenset({"text", "reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        return "verified-model-output"


def test_model_bridge_requires_canonical_agent_authorization():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-auth")
    system = CanonicalSystemFabric()
    identity, _ = AgentIdentityAuthority.generate("agent-auth")
    bridge = ModelFabricBridge(
        fabric,
        runtime_id="runtime-auth",
        execution_id="exec-auth",
        system_fabric=system,
        agent_identity=identity,
    )
    with pytest.raises(PermissionError):
        bridge.generate("hello")
    system.bind_agent_identity(identity, capabilities=("execute", "model:execute"))
    assert bridge.generate("hello") == "verified-model-output"


def test_model_bridge_rejects_missing_agent_identity_when_fabric_is_canonical():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-auth")
    system = CanonicalSystemFabric()
    with pytest.raises(PermissionError, match="model_agent_identity_required"):
        ModelFabricBridge(fabric, runtime_id="runtime-auth", execution_id="exec-auth", system_fabric=system)
