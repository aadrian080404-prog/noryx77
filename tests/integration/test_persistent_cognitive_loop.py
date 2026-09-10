from core.agent_continuity import ContinuityExercise
from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime
from core.universal_intelligence import UniversalIntelligenceFabric
from noryx7_runtime.model_fabric import ModelFabric


class LoopModel:
    name = "loop-model"
    capabilities = frozenset({"text", "reasoning"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        if "independent challenge" in prompt.lower() or "cross-check" in prompt.lower():
            return "SECONDARY CRITIQUE: identify uncertainty and a falsifiable next step."
        if "reconcile" in prompt.lower() or "reconciliation" in prompt.lower():
            return "RECONCILED RESEARCH: uncertainty retained and next step made falsifiable."
        return "PRIMARY HYPOTHESIS: bounded hypothesis with explicit uncertainty."


def _runtime(name="persistent-loop-test"):
    return OperationalNORYXRuntime(model_fabric=ModelFabric([LoopModel()], runtime_id=name))


def test_universal_route_invokes_bounded_lateral_cognition():
    fabric = UniversalIntelligenceFabric()
    task = TaskSpec(
        "lateral-task", "research", "Compare multiple scientific hypotheses and design an experiment", "Navier-Stokes and turbulence",
        risk_class="normal",
    )
    route = fabric.route(task)
    assert route.strategy == "branching_lateral"
    assert route.budget == "branching"


def test_persistent_loop_runs_primary_secondary_primary_and_stays_authority_bounded():
    runtime = _runtime()
    exercise = ContinuityExercise("exercise-e2e", "noryx7-llm", "bounded research exercise", 0.0)
    runtime._continuity_cycle(exercise)
    events = runtime.audit.snapshot()
    matching = [event for event in events if event.get("event") == "agent_continuity_exercise" and event.get("exercise_id") == "exercise-e2e"]
    assert matching
    event = matching[-1]
    assert event["interaction"] == ("noryx7-llm", "noryx7-secondary", "noryx7-llm")
    assert event["completed"] is True
    assert event["execution_authority"] == "none"
    assert event["external_side_effects"] is False

    for agent_id in ("noryx7-llm", "noryx7-secondary"):
        agent = runtime.router.get(agent_id)
        runtime.system_fabric.authorize_agent(agent.identity, "model:execute")
