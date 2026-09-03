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
        return tuple(Hypothesis(f"{task.task_id}:h{index}", task.task_id, step.objective, (step.step_id,)) for index, step in enumerate(plan.steps))

    def verify(self, hypotheses: tuple[Hypothesis, ...], task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(hypotheses, tuple) or not hypotheses:
            return VerificationResult(False, "hypothesis", "invalid_hypothesis_collection")
        ids = set()
        for hypothesis in hypotheses:
            if not isinstance(hypothesis, Hypothesis): return VerificationResult(False, "hypothesis", "invalid_hypothesis_type")
            if not isinstance(hypothesis.hypothesis_id, str) or not hypothesis.hypothesis_id.strip(): return VerificationResult(False, "hypothesis", "invalid_hypothesis_id")
            if hypothesis.hypothesis_id in ids: return VerificationResult(False, "hypothesis", "duplicate_hypothesis_id")
            ids.add(hypothesis.hypothesis_id)
            if hypothesis.task_id != task.task_id or not isinstance(hypothesis.statement, str) or not hypothesis.statement.strip() or not hypothesis.basis: return VerificationResult(False, "hypothesis", "invalid_hypothesis")
            if any(not isinstance(item, str) or not item.strip() for item in hypothesis.basis): return VerificationResult(False, "hypothesis", "invalid_hypothesis_basis")
        return VerificationResult(True, "hypothesis", "hypotheses_ok")


class InternalSimulator:
    """Pre-execution bounded feasibility check over the declared plan only."""
    def simulate(self, task: TaskSpec, hypotheses: tuple[Hypothesis, ...]) -> tuple[SimulationResult, ...]:
        if not isinstance(task, TaskSpec) or not isinstance(hypotheses, tuple): return ()
        return tuple(SimulationResult(h.hypothesis_id, bool(h.statement and h.task_id == task.task_id), "feasible" if h.statement and h.task_id == task.task_id else "invalid_hypothesis") for h in hypotheses if isinstance(h, Hypothesis))

    def verify(self, simulations: tuple[SimulationResult, ...]) -> VerificationResult:
        if not isinstance(simulations, tuple) or not simulations: return VerificationResult(False, "simulation", "no_simulations")
        ids = set()
        for item in simulations:
            if not isinstance(item, SimulationResult): return VerificationResult(False, "simulation", "invalid_simulation_type")
            if not isinstance(item.hypothesis_id, str) or not item.hypothesis_id.strip(): return VerificationResult(False, "simulation", "invalid_hypothesis_id")
            if item.hypothesis_id in ids: return VerificationResult(False, "simulation", "duplicate_simulation_id")
            ids.add(item.hypothesis_id)
            if not isinstance(item.feasible, bool): return VerificationResult(False, "simulation", "invalid_feasibility_flag")
            if not isinstance(item.reason, str) or not item.reason.strip(): return VerificationResult(False, "simulation", "invalid_simulation_reason")
            if item.feasible and item.reason != "feasible": return VerificationResult(False, "simulation", "feasible_reason_mismatch")
            if not item.feasible: return VerificationResult(False, "simulation", "simulation_rejected")
        return VerificationResult(True, "simulation", "simulation_ok")


class CrossChecker:
    """Checks that verified agent results map one-to-one to declared plan steps."""
    def verify(self, task: TaskSpec, results: tuple[AgentResult, ...], hypotheses: tuple[Hypothesis, ...]) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(results, tuple) or not isinstance(hypotheses, tuple): return VerificationResult(False, "cross_check", "invalid_cross_check_inputs")
        if not results: return VerificationResult(False, "cross_check", "no_results")
        if len(results) != len(hypotheses): return VerificationResult(False, "cross_check", "result_hypothesis_count_mismatch")
        if any(not isinstance(result, AgentResult) for result in results): return VerificationResult(False, "cross_check", "invalid_result_type")
        if any(not result.is_well_formed() for result in results): return VerificationResult(False, "cross_check", "malformed_result")
        if any(not isinstance(h, Hypothesis) for h in hypotheses): return VerificationResult(False, "cross_check", "invalid_hypothesis_type")
        expected_step_ids = [basis for h in hypotheses for basis in h.basis]
        if len(expected_step_ids) != len(hypotheses) or len(set(expected_step_ids)) != len(expected_step_ids): return VerificationResult(False, "cross_check", "duplicate_hypothesis_basis")
        if any(result.status != "completed" for result in results): return VerificationResult(False, "cross_check", "incomplete_result")
        for result in results:
            verification = result.verification
            if verification is None or not verification.is_well_formed() or not verification.valid: return VerificationResult(False, "cross_check", "unverified_result")
            if result.output is None: return VerificationResult(False, "cross_check", "null_output")
        result_task_ids = [result.task_id for result in results]
        if len(set(result_task_ids)) != len(result_task_ids): return VerificationResult(False, "cross_check", "duplicate_result_task")
        agent_ids = [result.agent_id for result in results]
        if len(set(agent_ids)) != len(agent_ids): return VerificationResult(False, "cross_check", "duplicate_agent_result")
        if set(result_task_ids) != set(expected_step_ids): return VerificationResult(False, "cross_check", "result_task_mismatch")
        for result in results:
            if result.verification.stage not in ("result", "agent_result", result.agent_id): return VerificationResult(False, "cross_check", "verification_identity_mismatch")
        return VerificationResult(True, "cross_check", "cross_check_ok")
