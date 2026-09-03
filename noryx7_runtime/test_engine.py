import pytest

from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def step(step_id, deps=()):
    return PlanStep(step_id, "tool.call", "target", {"step": step_id}, tuple(deps))


def test_dependencies_are_executed_in_deterministic_topological_order():
    seen = []
    engine = RuntimeEngine()
    result = engine.execute(
        Intent("run", "user"),
        [step("c", ("a", "b")), step("b"), step("a")],
        executor=lambda action: seen.append(action.step_id) or action.step_id,
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert seen == ["a", "b", "c"]


def test_budget_rejects_before_any_execution():
    called = []
    result = RuntimeEngine(max_actions=1).execute(
        Intent("run", "user"),
        [step("a"), step("b")],
        executor=lambda action: called.append(action.step_id),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "action_budget_exceeded"
    assert called == []


def test_failed_verification_never_commits():
    commits = []
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: "unsafe",
        verifier=lambda action, output: False,
        committer=lambda *args: commits.append(args),
    )
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "result_verification_failed"
    assert commits == []


def test_executor_exception_fails_closed():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: (_ for _ in ()).throw(RuntimeError("boom")),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "RuntimeError"


def test_committer_exception_does_not_report_success():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: "ok",
        verifier=lambda action, output: True,
        committer=lambda *args: (_ for _ in ()).throw(RuntimeError("storage")),
    )
    assert result.status is ExecutionStatus.FAILED


def test_missing_dependency_and_cycle_fail_closed():
    engine = RuntimeEngine()
    with pytest.raises(ValueError, match="missing dependency"):
        engine.execute(Intent("run", "user"), [step("a", ("missing",))], executor=lambda a: None, verifier=lambda a, o: True)
    with pytest.raises(ValueError, match="cyclic"):
        engine.execute(Intent("run", "user"), [step("a", ("b",)), step("b", ("a",))], executor=lambda a: None, verifier=lambda a, o: True)
