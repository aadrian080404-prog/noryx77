import pytest

from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def step(step_id: str) -> PlanStep:
    return PlanStep(step_id, "tool.call", "target", {"step": step_id})


def test_budget_rejection_is_created_to_rejected_transition():
    result = RuntimeEngine(max_actions=0).execute(Intent("run", "user"), [step("a")], executor=lambda action: "ok", verifier=lambda action, output: True)
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "action_budget_exceeded"


def test_success_is_running_to_succeeded_transition():
    result = RuntimeEngine().execute(Intent("run", "user"), [step("a")], executor=lambda action: "ok", verifier=lambda action, output: True)
    assert result.status is ExecutionStatus.SUCCEEDED


def test_verification_rejection_is_terminal_and_cannot_commit():
    committed = []
    result = RuntimeEngine().execute(Intent("run", "user"), [step("a")], executor=lambda action: "unsafe", verifier=lambda action, output: False, committer=lambda *args: committed.append(args))
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "result_verification_failed"
    assert committed == []


def test_deadline_transitions_running_to_cancelled_before_dispatch():
    calls = []
    ticks = iter((0.0, 2.0))
    def clock(): return next(ticks)
    result = RuntimeEngine(clock=clock).execute(Intent("run", "user"), [step("a")], executor=lambda action: calls.append(action) or "ok", verifier=lambda action, output: True, timeout_seconds=1.0)
    assert result.status is ExecutionStatus.CANCELLED
    assert result.error == "deadline_exceeded"
    assert calls == []


def test_scheduler_failure_does_not_create_terminal_result_from_invalid_plan():
    with pytest.raises(ValueError, match="cyclic"):
        RuntimeEngine().execute(Intent("run", "user"), [PlanStep("a", "tool.call", "target", {}, ("b",)), PlanStep("b", "tool.call", "target", {}, ("a",))], executor=lambda action: "ok", verifier=lambda action, output: True)
