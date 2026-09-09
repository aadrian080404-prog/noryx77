from core.identity import AgentIdentityAuthority
from core.llm.model_fabric_bridge import ModelFabricBridge
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.model_fabric import ModelFabric


class FakeModel:
    name = "fake-model"
    capabilities = frozenset({"text", "reasoning", "chat"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt: str, *, tools=()):
        return "MODEL FABRIC CANONICAL PASS"


def _bridge():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-test")
    system_fabric = CanonicalSystemFabric()
    identity, _ = AgentIdentityAuthority.generate("agent-model-test")
    bridge = ModelFabricBridge(
        fabric,
        runtime_id="runtime-test",
        execution_id="execution-test",
        system_fabric=system_fabric,
        agent_identity=identity,
    )
    return bridge, system_fabric, identity


def test_model_dispatch_is_bound_to_canonical_agent_capability():
    bridge, system_fabric, identity = _bridge()
    output = bridge.generate("test")
    assert output == "MODEL FABRIC CANONICAL PASS"
    authorization = system_fabric.authorize_agent(identity, "model:execute")
    assert authorization.identity_id == identity.agent_id
    assert "model:execute" in authorization.capabilities


def test_model_dispatch_records_digest_only_provenance():
    bridge, system_fabric, identity = _bridge()
    bridge.generate("sensitive user prompt")
    records = system_fabric.memory.snapshot()
    record = next(item for item in records if item.record_id == "execution:execution-test:model_completed")
    assert len(record.payload_digest) == 64
    assert len(record.provenance_digest) == 64
    assert b"sensitive user prompt" not in record.payload


def test_model_capability_is_not_implied_by_observe_only_binding():
    fabric = ModelFabric([FakeModel()], runtime_id="runtime-test")
    system_fabric = CanonicalSystemFabric()
    identity, _ = AgentIdentityAuthority.generate("agent-denied")
    system_fabric.bind_agent_identity(identity, capabilities=("observe",))
    bridge = ModelFabricBridge(
        fabric,
        runtime_id="runtime-test",
        execution_id="execution-denied",
        system_fabric=system_fabric,
        agent_identity=identity,
    )
    # The bridge must fail closed before model execution when the canonical
    # capability is absent; the bridge must not synthesize authority silently.
    try:
        bridge.generate("test")
    except PermissionError as exc:
        assert str(exc) == "capability_not_granted"
    else:
        raise AssertionError("model execution unexpectedly authorized")
