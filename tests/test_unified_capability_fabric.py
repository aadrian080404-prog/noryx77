from core.capability_fabric import CapabilityFabric
from core.contracts import TaskSpec
from core.planning import Planner
from core.tools import ToolExecutor
from core.actions import ActionGate
from core.policy import PolicyEngine
from core.security import SecurityBoundary
from core.verification import VerificationEngine
from core.limits import RuntimeLimits


def test_capability_fabric_routes_real_world_intents():
    fabric = CapabilityFabric()
    assert fabric.classify("prenotami un volo per Roma").capability == "flights"
    assert fabric.classify("paga la bolletta della luce").capability == "payments"
    assert fabric.classify("prepara il contratto").capability == "contracts"
    assert fabric.classify("gestisci la pratica con l'INPS").capability == "bureaucracy"


def test_planner_selects_external_capability_from_natural_language():
    task = TaskSpec("task-1", "browser_request", "prenotami un volo per Roma", "voglio partire venerdì")
    plan = Planner(max_steps=2).build(task)
    assert plan.steps[0].action_type == "flights"
    assert plan.steps[0].risk_class == "high"


def test_external_capability_is_fail_closed_without_authorization():
    verifier = VerificationEngine()
    policy = PolicyEngine()
    gate = ActionGate(policy, SecurityBoundary(policy, verifier), RuntimeLimits())
    executor = ToolExecutor(gate, verifier)
    from core.contracts import ActionSpec
    action = ActionSpec("flight-1", "flights", target="Rome", parameters={"execution_id": "exec-1"}, execution_id="exec-1")
    output, check = executor.execute(action, execution_id="exec-1")
    assert output is None
    assert check.valid is False
    assert check.reason == "authorization_required"
