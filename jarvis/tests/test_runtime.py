import pytest
from jarvis.core.contracts import Request, Plan, PlanStep, ActionResult
from jarvis.core.runtime import JarvisRuntime
from jarvis.core.state import JarvisStateStore


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


def test_canonical_fabric_marks_jarvis_committed_only_after_state_commit():
    runtime = JarvisRuntime()
    request = Request("ordered", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    runtime.grant("user", "tool", "target")

    assert runtime.execute(request, plan)[0].success
    record_ids = {record.record_id for record in runtime.system_fabric.memory.snapshot()}
    assert "execution:ordered:jarvis_received" in record_ids
    assert "execution:ordered:jarvis_verified" in record_ids
    assert "execution:ordered:jarvis_committed" in record_ids
    assert "execution:ordered:jarvis_execution_rejected" not in record_ids


class _FailingCommitStore(JarvisStateStore):
    def commit(self, *args, **kwargs):
        raise RuntimeError("forced_state_commit_failure")


def test_canonical_fabric_cannot_claim_jarvis_commit_when_state_commit_fails():
    runtime = JarvisRuntime(state_store=_FailingCommitStore())
    request = Request("commit-failure", "user")
    plan = Plan(request.request_id, (PlanStep("a", "tool", "target", {}),))
    runtime.registry.register("tool", lambda s: ActionResult(s.step_id, True, "ok"))
    runtime.grant("user", "tool", "target")

    assert runtime.execute(request, plan) == ()
    record_ids = {record.record_id for record in runtime.system_fabric.memory.snapshot()}
    assert "execution:commit-failure:jarvis_verified" in record_ids
    assert "execution:commit-failure:jarvis_committed" not in record_ids
    assert "execution:commit-failure:jarvis_rejected" in record_ids
