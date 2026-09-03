import pytest

from .adapters import CapabilityAdapter
from .capabilities import Capability, CapabilityBroker
from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def step(step_id, deps=(), action_type="tool.call"):
    return PlanStep(step_id, action_type, "target", {"step": step_id}, tuple(deps))


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


def test_capability_adapter_is_the_effect_boundary_when_configured():
    seen = []
    broker = CapabilityBroker({
        "tool": Capability("tool", frozenset({"tool.call"}), lambda action: seen.append(action) or "ok")
    })
    result = RuntimeEngine(adapter=CapabilityAdapter(broker)).execute(
        Intent("run", "user"),
        [step("a")],
        verifier=lambda action, output: output == "ok",
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert len(seen) == 1
    assert seen[0].execution_id == result.execution_id
    assert seen[0].principal_id == "user"


def test_adapter_rejects_unregistered_effect_type_before_execution():
    result = RuntimeEngine(adapter=CapabilityAdapter(CapabilityBroker())).execute(
        Intent("run", "user"),
        [step("a")],
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "LookupError"


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


def test_non_json_output_fails_closed():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: object(),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error in {"TypeError", "ValueError"}


def test_missing_dependency_and_cycle_fail_closed():
    engine = RuntimeEngine()
    with pytest.raises(ValueError, match="missing dependency"):
        engine.execute(Intent("run", "user"), [step("a", ("missing",))], executor=lambda a: None, verifier=lambda a, o: True)
    with pytest.raises(ValueError, match="cyclic"):
        engine.execute(Intent("run", "user"), [step("a", ("b",)), step("b", ("a",))], executor=lambda a: None, verifier=lambda a, o: True)
