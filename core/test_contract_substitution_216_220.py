"""Adversarial regression tests for contract-substitution boundaries (Attacks 216-220)."""

from dataclasses import replace

from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan
from .reasoning import CrossChecker, Hypothesis, HypothesisEngine, InternalSimulator


class _VerificationResultSubclass(VerificationResult):
    pass


class _AgentResultSubclass(AgentResult):
    pass


class _HypothesisSubclass(Hypothesis):
    pass


class _TaskSpecSubclass(TaskSpec):
    pass


def _task() -> TaskSpec:
    return TaskSpec(
        task_id="task-216",
        task_type="analysis",
        objective="inspect",
        input={},
        constraints={},
        verification_requirements=("string",),
        risk_class="normal",
    )


def _hypothesis(task: TaskSpec) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=f"{task.task_id}:h0",
        task_id=task.task_id,
        statement="inspect",
        basis=(f"{task.task_id}:s0",),
    )


def _plan(task: TaskSpec) -> Plan:
    # Use the repository's existing Plan/step contract through its public constructor.
    from .planning import PlanStep

    step = PlanStep(step_id=f"{task.task_id}:s0", objective=task.objective)
    return Plan(task_id=task.task_id, steps=(step,))


def test_attack_216_crosschecker_rejects_verification_subclass():
    task = _task()
    hypothesis = _hypothesis(task)
    result = AgentResult(
        agent_id="agent-1",
        task_id=hypothesis.basis[0],
        status="completed",
        output="ok",
        verification=_VerificationResultSubclass(True, "result", "ok"),
    )
    verdict = CrossChecker().verify(task, (result,), (hypothesis,))
    assert verdict.valid is False
    assert verdict.reason == "unverified_result"


def test_attack_217_crosschecker_rejects_agent_result_subclass():
    task = _task()
    hypothesis = _hypothesis(task)
    result = _AgentResultSubclass(
        agent_id="agent-1",
        task_id=hypothesis.basis[0],
        status="completed",
        output="ok",
        verification=VerificationResult(True, "result", "ok"),
    )
    verdict = CrossChecker().verify(task, (result,), (hypothesis,))
    assert verdict.valid is False
    assert verdict.reason == "invalid_result_type"


def test_attack_218_hypothesis_engine_rejects_hypothesis_subclass():
    task = _task()
    hypothesis = _HypothesisSubclass(
        hypothesis_id=f"{task.task_id}:h0",
        task_id=task.task_id,
        statement="inspect",
        basis=(f"{task.task_id}:s0",),
    )
    verdict = HypothesisEngine().verify((hypothesis,), task)
    assert verdict.valid is False
    assert verdict.reason == "invalid_hypothesis_type"


def test_attack_219_simulator_rejects_hypothesis_subclass():
    task = _task()
    hypothesis = _HypothesisSubclass(
        hypothesis_id=f"{task.task_id}:h0",
        task_id=task.task_id,
        statement="inspect",
        basis=(f"{task.task_id}:s0",),
    )
    simulations = InternalSimulator().simulate(task, (hypothesis,))
    assert len(simulations) == 1
    assert simulations[0].feasible is False
    assert simulations[0].reason == "invalid_hypothesis"


def test_attack_220_crosschecker_rejects_task_contract_subclass():
    base = _task()
    task = _TaskSpecSubclass(**base.__dict__)
    hypothesis = _hypothesis(base)
    result = AgentResult(
        agent_id="agent-1",
        task_id=hypothesis.basis[0],
        status="completed",
        output="ok",
        verification=VerificationResult(True, "result", "ok"),
    )
    verdict = CrossChecker().verify(task, (result,), (hypothesis,))
    assert verdict.valid is False
    assert verdict.reason == "invalid_cross_check_inputs"
