import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.runtime import JarvisRuntime

def test_runtime_requires_explicit_grant_and_registered_capability():
    runtime = JarvisRuntime()
    request = Request("run", "user")
    step = PlanStep("a", "tool", "target", {})
    plan = Plan(request.request_id, (step,))
    runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    with pytest.raises(PermissionError, match="capability_denied"):
        runtime.execute(request, plan)
    runtime.grant("user", "tool", "target")
    result = runtime.execute(request, plan)
    assert result[0].success
    assert result[0].output == "ok"

def test_runtime_rejects_plan_from_another_request():
    runtime = JarvisRuntime()
    first = Request("one", "user")
    second = Request("two", "user")
    plan = Plan(first.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(PermissionError, match="request_identity_mismatch"):
        runtime.execute(second, plan)
