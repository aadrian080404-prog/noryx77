from dataclasses import dataclass

from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    task_id: str
    statement: str
    basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class SimulationResult:
    hypothesis_id: str
    feasible: bool
    reason: str


class HypothesisEngine:
    """Bounded, inspectable hypothesis generation; never exposes hidden reasoning traces."""

    def generate(self, task: TaskSpec, plan: Plan) -> tuple[Hypothesis, ...]:
        if not isinstance(task, TaskSpec) or not isinstance(plan, Plan) or not plan.steps:
            return ()
        return tuple(
            Hypothesis(
                hypothesis_id=f"{task.task_id}:h{index}",
                task_id=task.task_id,
                statement=step.objective,
                basis=(step.step_id,),
            )
            for index, step in enumerate(plan.steps)
        )

    def verify(self, hypotheses: tuple[Hypothesis, ...], task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(hypotheses, tuple) or not hypotheses:
            return VerificationResult(False, "hypothesis", "invalid_hypothesis_collection")
        ids = set()
        for hypothesis in hypotheses:
            if not isinstance(hypothesis, Hypothesis):
                return VerificationResult(False, "hypothesis", "invalid_hypothesis_type")
            if hypothesis.hypothesis_id in ids:
                return VerificationResult(False, "hypothesis", "duplicate_hypothesis_id")
            ids.add(hypothesis.hypothesis_id)
            if hypothesis.task_id != task.task_id or not hypothesis.statement or not hypothesis.basis:
                return VerificationResult(False, "hypothesis", "invalid_hypothesis")
            if any(not isinstance(item, str) or not item for item in hypothesis.basis):
                return VerificationResult(False, "hypothesis", "invalid_hypothesis_basis")
        return VerificationResult(True, "hypothesis", "hypotheses_ok")


class InternalSimulator:
    """Pre-execution bounded feasibility check over the declared plan only."""

    def simulate(self, task: TaskSpec, hypotheses: tuple[Hypothesis, ...]) -> tuple[SimulationResult, ...]:
        if not isinstance(task, TaskSpec) or not isinstance(hypotheses, tuple):
            return ()
        return tuple(
            SimulationResult(
                hypothesis.hypothesis_id,
                bool(hypothesis.statement and hypothesis.task_id == task.task_id),
                "feasible" if hypothesis.statement and hypothesis.task_id == task.task_id else "invalid_hypothesis",
            )
            for hypothesis in hypotheses
            if isinstance(hypothesis, Hypothesis)
        )

    def verify(self, simulations: tuple[SimulationResult, ...]) -> VerificationResult:
        if not isinstance(simulations, tuple) or not simulations:
            return VerificationResult(False, "simulation", "no_simulations")
        ids = set()
        for item in simulations:
            if not isinstance(item, SimulationResult):
                return VerificationResult(False, "simulation", "invalid_simulation_type")
            if item.hypothesis_id in ids:
                return VerificationResult(False, "simulation", "duplicate_simulation_id")
            ids.add(item.hypothesis_id)
            if not item.feasible:
                return VerificationResult(False, "simulation", "simulation_rejected")
        return VerificationResult(True, "simulation", "simulation_ok")


class CrossChecker:
    """Checks that verified agent results map one-to-one to declared plan steps."""

    def verify(self, task: TaskSpec, results: tuple[AgentResult, ...], hypotheses: tuple[Hypothesis, ...]) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(results, tuple) or not isinstance(hypotheses, tuple):
            return VerificationResult(False, "cross_check", "invalid_cross_check_inputs")
        if not results:
            return VerificationResult(False, "cross_check", "no_results")
        if len(results) != len(hypotheses):
            return VerificationResult(False, "cross_check", "result_hypothesis_count_mismatch")
        if any(not isinstance(result, AgentResult) for result in results):
            return VerificationResult(False, "cross_check", "invalid_result_type")
        if any(not isinstance(hypothesis, Hypothesis) for hypothesis in hypotheses):
            return VerificationResult(False, "cross_check", "invalid_hypothesis_type")
        expected_step_ids = [basis for hypothesis in hypotheses for basis in hypothesis.basis]
        if len(expected_step_ids) != len(hypotheses) or len(set(expected_step_ids)) != len(expected_step_ids):
            return VerificationResult(False, "cross_check", "duplicate_hypothesis_basis")
        result_ids = [result.task_id for result in results]
        if len(set(result_ids)) != len(result_ids):
            return VerificationResult(False, "cross_check", "duplicate_result_task")
        if set(result_ids) != set(expected_step_ids):
            return VerificationResult(False, "cross_check", "result_task_mismatch")
        if any(result.status != "completed" for result in results):
            return VerificationResult(False, "cross_check", "incomplete_result")
        return VerificationResult(True, "cross_check", "cross_check_ok")
