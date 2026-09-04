import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.orchestrator import JarvisOrchestrator
from jarvis.core.policy import Policy

def test_action_requires_authorization_and_dependencies():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("b", "tool", "target", {}, ("a",)),))
    with pytest.raises(ValueError, match="dependencies"):
        JarvisOrchestrator().execute(request, plan, lambda s: ActionResult(s.step_id, True))

def test_executor_result_type_is_enforced():
    request = Request("do", "user")
    step = PlanStep("a", "tool", "target", {})
    policy = Policy()
    policy.grant("user", "tool", "target")
    plan = Plan(request.request_id, (step,))
    with pytest.raises(TypeError):
        JarvisOrchestrator(policy=policy).execute(request, plan, lambda s: "ok")

def test_policy_denies_without_explicit_grant():
    policy = Policy()
    assert not policy.authorize("user", "tool", "target")
