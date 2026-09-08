import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.orchestrator import JarvisOrchestrator
from jarvis.core.policy import Policy

def granted():
    policy = Policy()
    policy.grant("user", "tool", "target")
    return policy

def test_action_requires_authorization_and_dependencies():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("b", "tool", "target", {}, ("a",)),))
    with pytest.raises(ValueError, match="dependencies"):
        JarvisOrchestrator().execute(request, plan, lambda s: ActionResult(s.step_id, True))

def test_executor_result_type_is_enforced():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(TypeError):
        JarvisOrchestrator(policy=granted()).execute(request, plan, lambda s: "ok")

def test_policy_denies_without_explicit_grant():
    assert not Policy().authorize("user", "tool", "target")

def test_plan_cannot_be_replayed_against_another_request():
    request = Request("do", "user")
    plan = Plan("different-request", (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(ValueError, match="request_plan_mismatch"):
        JarvisOrchestrator(policy=granted()).execute(request, plan, lambda s: ActionResult(s.step_id, True))

def test_duplicate_step_ids_are_rejected():
    request = Request("do", "user")
    steps = (PlanStep("a", "tool", "target", {}), PlanStep("a", "tool", "target", {}))
    with pytest.raises(ValueError, match="duplicate_step_id"):
        JarvisOrchestrator(policy=granted()).execute(request, Plan(request.request_id, steps), lambda s: ActionResult(s.step_id, True))

def test_result_cannot_be_retargeted_to_another_step():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(ValueError, match="result_step_mismatch"):
        JarvisOrchestrator(policy=granted()).execute(request, plan, lambda s: ActionResult("other", True))

def test_executor_exception_becomes_failed_action_result():
    request = Request("do", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    result = JarvisOrchestrator(policy=granted()).execute(request, plan, lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
    assert result[0].success is False
    assert result[0].error == "RuntimeError"
