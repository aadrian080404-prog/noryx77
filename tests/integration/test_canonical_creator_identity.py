from core.identity import AgentIdentityAuthority
from core.llm.agent import LLMBackedAgent, SecondaryLLMBackedAgent
from core.system_identity import (
    CANONICAL_SYSTEM_IDENTITY,
    CREATOR_ID,
    SYSTEM_ID,
)
from gateway.runtime_adapter import RuntimeAdapter


class FakeModelFabric:
    def generate(self, prompt: str) -> str:
        return "ok"


def test_canonical_system_identity_is_well_formed():
    identity = CANONICAL_SYSTEM_IDENTITY
    assert identity.is_well_formed()
    assert identity.system_id == SYSTEM_ID == "NORYX7"
    assert identity.creator == CREATOR_ID == "Adrian Aristodemo"


def test_primary_and_secondary_agents_expose_creator_identity():
    primary_identity, _ = AgentIdentityAuthority.generate("noryx7-llm")
    primary = LLMBackedAgent(FakeModelFabric(), identity=primary_identity)
    secondary_identity, _ = AgentIdentityAuthority.generate("noryx7-secondary")
    secondary = SecondaryLLMBackedAgent(FakeModelFabric(), identity=secondary_identity)

    assert primary.describe()["creator"] == CREATOR_ID
    assert secondary.describe()["creator"] == CREATOR_ID
    prompt = primary._build_prompt(
        __import__("core.contracts", fromlist=["TaskSpec"]).TaskSpec(
            task_id="t",
            task_type="test",
            objective="identity check",
            input="identity check",
            execution_id="e",
        )
    )
    assert "Adrian Aristodemo" in prompt
    assert "created and invited NORYX7" in prompt


def test_gateway_task_propagates_canonical_creator_identity():
    task = RuntimeAdapter._build_task(
        client_id="web",
        text="hello",
        execution_id="exec-1",
    )
    assert task.constraints["_noryx7_system_id"] == SYSTEM_ID
    assert task.constraints["_noryx7_creator"] == CREATOR_ID
