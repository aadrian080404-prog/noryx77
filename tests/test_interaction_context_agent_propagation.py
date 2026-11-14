from core.contracts import TaskSpec
from core.runtime import NORYXRuntime
from core.user_understanding import UnderstandingConsent, UserUnderstandingEngine
from noryx7_runtime.model_fabric import ModelFabric


class ContextAwareModel:
    name = "context-aware"
    capabilities = frozenset({"text", "reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, *, tools=()):
        self.prompts.append(prompt)
        return "CONTEXT-AWARE RESPONSE: bounded result without claiming external execution."


def test_user_understanding_context_reaches_llm_prompt_through_canonical_runtime():
    model = ContextAwareModel()
    fabric = ModelFabric([model], runtime_id="interaction-context-e2e")
    understanding = UserUnderstandingEngine(consent=UnderstandingConsent.PRE_INTERACTION)
    runtime = NORYXRuntime(model_fabric=fabric, user_understanding=understanding)
    task = TaskSpec(
        task_id="interaction-context-e2e-task",
        task_type="conversation",
        objective="Answer the user while respecting the derived interaction context.",
        input="I prefer detailed technical explanations.",
        constraints={},
        verification_requirements=("agent_result",),
        risk_class="normal",
        execution_id="execution-interaction-context-e2e",
    )

    result = runtime.run_hypersynth(task)

    assert result["status"] == "completed"
    assert model.prompts
    prompt = model.prompts[0]
    assert "=== USER INTERACTION CONTEXT ===" in prompt
    assert "detailed" in prompt
    assert "execution-interaction-context-e2e" in prompt
    assert any(event.get("event") == "user_understanding_derived" for event in runtime.audit.snapshot())
