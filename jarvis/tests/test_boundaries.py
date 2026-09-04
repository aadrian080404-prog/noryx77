import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.orchestrator import JarvisOrchestrator

def test_action_requires_authorization_and_dependencies():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("b", "tool", "target", {}, ("a",)),))
    with pytest.raises(ValueError, match="dependencies"):
        JarvisOrchestrator().execute(request, plan, lambda s: ActionResult(s.step_id, True))

def test_executor_result_type_is_enforced():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(TypeError):
        JarvisOrchestrator().execute(request, plan, lambda s: "ok")
