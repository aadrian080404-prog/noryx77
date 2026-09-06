import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.runtime import JarvisRuntime


def test_runtime_requires_explicit_grant_and_registered_capability():
    runtime = JarvisRuntime(); request = Request("run", "user"); step = PlanStep("a", "tool", "target", {}); plan = Plan(request.request_id, (step,)); runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    with pytest.raises(PermissionError, match="capability_denied"): runtime.execute(request, plan)
    runtime.grant("user", "tool", "target"); result = runtime.execute(request, plan)
    assert result[0].success and result[0].output == "ok"


def test_runtime_rejects_plan_from_another_request():
    runtime = JarvisRuntime(); first = Request("one", "user"); second = Request("two", "user"); plan = Plan(first.request_id, (PlanStep("a", "tool", "target", {}),))
    with pytest.raises(PermissionError, match="request_identity_mismatch"): runtime.execute(second, plan)


def test_runtime_reserves_execution_before_side_effect_and_blocks_replay():
    runtime = JarvisRuntime(); request = Request("run", "user"); plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),)); calls = []
    runtime.registry.register("tool", lambda s: calls.append(s.step_id) or ActionResult(s.step_id, True, "ok")); runtime.grant("user", "tool", "target")
    first = runtime.execute(request, plan); second = runtime.execute(request, plan)
    assert first[0].success and second == () and calls == ["a"]
    assert runtime.state.get(request.request_id) is not None


def test_unauthorized_request_does_not_consume_execution_reservation():
    runtime = JarvisRuntime(); request = Request("run", "user"); plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),)); runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    with pytest.raises(PermissionError, match="capability_denied"): runtime.execute(request, plan)
    assert runtime.state.reservation(request.request_id) is None
    runtime.grant("user", "tool", "target")
    assert runtime.execute(request, plan)[0].success
