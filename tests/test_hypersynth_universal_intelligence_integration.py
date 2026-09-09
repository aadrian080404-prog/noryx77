from core.contracts import TaskSpec
from core.hypersynth import Hypersynth
from core.universal_intelligence import UniversalIntelligenceFabric
from core.verification import VerificationEngine
from core.router import ResourceRouter
from core.agents import DeterministicAgent


def _task(objective="Explain this software architecture", task_id="uif-e2e"):
    return TaskSpec(
        task_id=task_id,
        task_type="conversation",
        objective=objective,
        input="Please analyze the code and architecture.",
        constraints={},
        verification_requirements=("agent_result",),
        risk_class="normal",
        execution_id=f"execution-{task_id}",
    )


def test_uif_routes_software_task_to_specialist_budget():
    route = UniversalIntelligenceFabric().route(_task())
    assert route.is_well_formed()
    assert route.domain == "software_engineering"
    assert route.budget == "specialist"
    assert route.strategy in {"pythagorean", "apollonian", "eurelian"}


def test_hypersynth_executes_uif_route_and_verifies_fabric_result():
    verifier = VerificationEngine()
    router = ResourceRouter()
    router.register(DeterministicAgent(verifier))
    runtime = Hypersynth(verifier, router, max_steps=1, max_agents=1)
    result = runtime.run(_task())
    assert result["status"] == "completed"
    assert result["specialist_route"].domain == "software_engineering"
    assert result["universal_intelligence"].commit_eligible is True
    assert result["universal_intelligence"].verification.valid is True
    events = runtime.audit.snapshot()
    assert any(event.get("event") == "universal_intelligence_route" for event in events)
    assert any(event.get("event") == "universal_intelligence_assessed" for event in events)


def test_uif_route_never_grants_authority():
    route = UniversalIntelligenceFabric().route(_task("Execute a financial transfer and approve the transaction"))
    assert route.domain == "finance_economics"
    assert not hasattr(route, "authorize")
    assert not hasattr(route, "commit")
