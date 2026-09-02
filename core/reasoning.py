from dataclasses import dataclass

from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan
from .validation_requirements import VALID_VERIFICATION_REQUIREMENTS


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    task_id: str
    statement: str
    basis: tuple[str, ...] = ()
    context_version: int | None = None
    context_source_ids: tuple[str, ...] = ()


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
        if plan.task_id != task.task_id:
            return ()
        return tuple(
            Hypothesis(
                f"{task.task_id}:h{index}",
                task.task_id,
                step.objective,
                (step.step_id,),
                plan.context_version,
                plan.context_source_ids,
            )
            for index, step in enumerate(plan.steps)
        )

    def verify(self, hypotheses: tuple[Hypothesis, ...], task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(hypotheses, tuple) or not hypotheses:
            return VerificationResult(False, "hypothesis", "invalid_hypothesis_collection")
        ids = set()
        for hypothesis in hypotheses:
            if type(hypothesis) is not Hypothesis: return VerificationResult(False, "hypothesis", "invalid_hypothesis_type")
            if not isinstance(hypothesis.hypothesis_id, str) or not hypothesis.hypothesis_id.strip(): return VerificationResult(False, "hypothesis", "invalid_hypothesis_id")
            if hypothesis.hypothesis_id in ids: return VerificationResult(False, "hypothesis", "duplicate_hypothesis_id")
            ids.add(hypothesis.hypothesis_id)
            if hypothesis.task_id != task.task_id or not isinstance(hypothesis.statement, str) or not hypothesis.statement.strip() or not hypothesis.basis: return VerificationResult(False, "hypothesis", "invalid_hypothesis")
            if any(not isinstance(item, str) or not item.strip() for item in hypothesis.basis): return VerificationResult(False, "hypothesis", "invalid_hypothesis_basis")
            if hypothesis.context_version is not None:
                if isinstance(hypothesis.context_version, bool) or not isinstance(hypothesis.context_version, int) or hypothesis.context_version < 1:
                    return VerificationResult(False, "hypothesis", "invalid_context_version")
                if not isinstance(hypothesis.context_source_ids, tuple) or not hypothesis.context_source_ids or hypothesis.context_source_ids[0] != task.task_id:
                    return VerificationResult(False, "hypothesis", "invalid_context_sources")
                if any(not isinstance(source_id, str) or not source_id.strip() for source_id in hypothesis.context_source_ids):
                    return VerificationResult(False, "hypothesis", "invalid_context_sources")
            elif hypothesis.context_source_ids:
                return VerificationResult(False, "hypothesis", "unexpected_context_binding")
        return VerificationResult(True, "hypothesis", "hypotheses_ok")

    def verify_against_plan(self, hypotheses: tuple[Hypothesis, ...], plan: Plan, task: TaskSpec) -> VerificationResult:
        """Verify that each hypothesis is bound to the exact verified planning context."""
        if not isinstance(plan, Plan):
            return VerificationResult(False, "hypothesis", "invalid_plan")
        if plan.task_id != task.task_id:
            return VerificationResult(False, "hypothesis", "plan_task_mismatch")
        if not isinstance(hypotheses, tuple) or len(hypotheses) != len(plan.steps) or not hypotheses:
            return VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch")
        for hypothesis, step in zip(hypotheses, plan.steps):
            if type(hypothesis) is not Hypothesis:
                return VerificationResult(False, "hypothesis", "invalid_hypothesis_type")
            if hypothesis.context_version != plan.context_version or hypothesis.context_source_ids != plan.context_source_ids:
                return VerificationResult(False, "hypothesis", "hypothesis_context_mismatch")
            if hypothesis.task_id != task.task_id or hypothesis.statement != step.objective:
                return VerificationResult(False, "hypothesis", "hypothesis_plan_binding_mismatch")
            if hypothesis.basis != (step.step_id,):
                return VerificationResult(False, "hypothesis", "hypothesis_step_mismatch")
        return VerificationResult(True, "hypothesis", "hypothesis_plan_binding_ok")


class InternalSimulator:
    """Pre-execution bounded feasibility check over declared hypotheses and task constraints."""

    MAX_SIMULATIONS = 8

    def simulate(self, task: TaskSpec, hypotheses: tuple[Hypothesis, ...]) -> tuple[SimulationResult, ...]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed() or not isinstance(hypotheses, tuple) or not hypotheses:
            return ()
        if len(hypotheses) > self.MAX_SIMULATIONS:
            return tuple(SimulationResult("__invalid__", False, "simulation_bounds_exceeded") for _ in range(1))
        ids = set()
        expected_sources = None
        expected_version = None
        results = []
        for hypothesis in hypotheses:
            if type(hypothesis) is not Hypothesis:
                return tuple(SimulationResult("__invalid__", False, "invalid_hypothesis") for _ in range(1))
            if not isinstance(hypothesis.hypothesis_id, str) or not hypothesis.hypothesis_id.strip() or hypothesis.hypothesis_id in ids:
                return tuple(SimulationResult(hypothesis.hypothesis_id if isinstance(hypothesis.hypothesis_id, str) else "__invalid__", False, "invalid_hypothesis_id") for _ in range(1))
            if hypothesis.task_id != task.task_id:
                return (SimulationResult(hypothesis.hypothesis_id, False, "hypothesis_task_mismatch"),)
            if not isinstance(hypothesis.statement, str) or not hypothesis.statement.strip():
                return (SimulationResult(hypothesis.hypothesis_id, False, "invalid_hypothesis"),)
            if not isinstance(hypothesis.basis, tuple) or len(hypothesis.basis) != 1:
                return (SimulationResult(hypothesis.hypothesis_id, False, "invalid_hypothesis_basis"),)
            basis = hypothesis.basis[0]
            if not isinstance(basis, str) or not basis.startswith(task.task_id + ":"):
                return (SimulationResult(hypothesis.hypothesis_id, False, "hypothesis_basis_identity_mismatch"),)
            if hypothesis.context_version is not None:
                if isinstance(hypothesis.context_version, bool) or not isinstance(hypothesis.context_version, int) or hypothesis.context_version < 1:
                    return (SimulationResult(hypothesis.hypothesis_id, False, "invalid_context_version"),)
                if not isinstance(hypothesis.context_source_ids, tuple) or not hypothesis.context_source_ids or hypothesis.context_source_ids[0] != task.task_id:
                    return (SimulationResult(hypothesis.hypothesis_id, False, "invalid_context_sources"),)
                if expected_version is None:
                    expected_version = hypothesis.context_version
                    expected_sources = hypothesis.context_source_ids
                elif hypothesis.context_version != expected_version or hypothesis.context_source_ids != expected_sources:
                    return (SimulationResult(hypothesis.hypothesis_id, False, "context_binding_mismatch"),)
            elif hypothesis.context_source_ids:
                return (SimulationResult(hypothesis.hypothesis_id, False, "unexpected_context_binding"),)
            ids.add(hypothesis.hypothesis_id)
            results.append(SimulationResult(hypothesis.hypothesis_id, True, "feasible"))
        max_steps = task.constraints.get("max_steps") if hasattr(task.constraints, "get") else None
        if max_steps is not None:
            if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
                return (SimulationResult("__constraints__", False, "invalid_max_steps_constraint"),)
            if len(hypotheses) > max_steps:
                return (SimulationResult("__constraints__", False, "step_budget_exceeded"),)
        return tuple(results)

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
        if any(type(result) is not AgentResult for result in results): return VerificationResult(False, "cross_check", "invalid_result_type")
        if any(not result.is_well_formed() for result in results): return VerificationResult(False, "cross_check", "malformed_result")
        if any(type(h) is not Hypothesis for h in hypotheses): return VerificationResult(False, "cross_check", "invalid_hypothesis_type")
        if any(h.task_id != task.task_id for h in hypotheses): return VerificationResult(False, "cross_check", "hypothesis_task_mismatch")
        if any(not isinstance(h.hypothesis_id, str) or not h.hypothesis_id.strip() for h in hypotheses): return VerificationResult(False, "cross_check", "invalid_hypothesis_id")
        if len({h.hypothesis_id for h in hypotheses}) != len(hypotheses): return VerificationResult(False, "cross_check", "duplicate_hypothesis_id")
        for hypothesis in hypotheses:
            if not isinstance(hypothesis.basis, tuple) or len(hypothesis.basis) != 1:
                return VerificationResult(False, "cross_check", "invalid_hypothesis_basis")
            basis = hypothesis.basis[0]
            if not isinstance(basis, str) or not basis.strip() or not basis.startswith(task.task_id + ":"):
                return VerificationResult(False, "cross_check", "hypothesis_basis_identity_mismatch")
        expected_step_ids = [h.basis[0] for h in hypotheses]
        if len(set(expected_step_ids)) != len(expected_step_ids): return VerificationResult(False, "cross_check", "duplicate_hypothesis_basis")
        if any(result.status != "completed" for result in results): return VerificationResult(False, "cross_check", "incomplete_result")
        for result in results:
            verification = result.verification
            if type(verification) is not VerificationResult or not verification.is_well_formed() or not verification.valid: return VerificationResult(False, "cross_check", "unverified_result")
            if result.output is None: return VerificationResult(False, "cross_check", "null_output")
            if isinstance(result.output, (str, bytes)) and not result.output: return VerificationResult(False, "cross_check", "empty_output")
            for requirement in task.verification_requirements:
                if requirement not in VALID_VERIFICATION_REQUIREMENTS:
                    return VerificationResult(False, "cross_check", "unsupported_output_requirement")
                if requirement == "string" and not isinstance(result.output, str):
                    return VerificationResult(False, "cross_check", "output_requirement_mismatch")
        result_task_ids = [result.task_id for result in results]
        if len(set(result_task_ids)) != len(result_task_ids): return VerificationResult(False, "cross_check", "duplicate_result_task")
        agent_ids = [result.agent_id for result in results]
        if len(set(agent_ids)) != len(agent_ids): return VerificationResult(False, "cross_check", "duplicate_agent_result")
        if result_task_ids != expected_step_ids: return VerificationResult(False, "cross_check", "result_task_mismatch")
        for result in results:
            if result.verification.stage not in ("result", "agent_result", result.agent_id): return VerificationResult(False, "cross_check", "verification_identity_mismatch")
        return VerificationResult(True, "cross_check", "cross_check_ok")
