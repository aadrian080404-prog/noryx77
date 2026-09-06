from __future__ import annotations

from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan
from .reasoning import Hypothesis, SimulationResult


class IndependentChallengeVerifier:
    """Independent structural challenge path; never trusts the primary verifier's decision."""

    def verify(self, task: TaskSpec, plan: Plan, hypotheses: tuple[Hypothesis, ...],
               simulations: tuple[SimulationResult, ...], results: tuple[AgentResult, ...],
               final_output) -> VerificationResult:
        if not isinstance(task, TaskSpec) or not isinstance(plan, Plan):
            return VerificationResult(False, "challenge_verification", "invalid_inputs")
        if not isinstance(hypotheses, tuple) or not isinstance(simulations, tuple) or not isinstance(results, tuple):
            return VerificationResult(False, "challenge_verification", "invalid_collections")
        if not plan.steps or len(plan.steps) != len(hypotheses) or len(hypotheses) != len(simulations) or len(simulations) != len(results):
            return VerificationResult(False, "challenge_verification", "pipeline_shape_mismatch")
        if plan.task_id != task.task_id:
            return VerificationResult(False, "challenge_verification", "plan_task_mismatch")
        expected_steps = tuple(step.step_id for step in plan.steps)
        if len(set(expected_steps)) != len(expected_steps):
            return VerificationResult(False, "challenge_verification", "duplicate_step_identity")
        expected_hypotheses = tuple(h.hypothesis_id for h in hypotheses if isinstance(h, Hypothesis))
        if len(expected_hypotheses) != len(hypotheses) or len(set(expected_hypotheses)) != len(expected_hypotheses):
            return VerificationResult(False, "challenge_verification", "invalid_hypothesis_identity")
        if tuple(s.hypothesis_id for s in simulations if isinstance(s, SimulationResult)) != expected_hypotheses:
            return VerificationResult(False, "challenge_verification", "simulation_identity_mismatch")
        if any(not isinstance(r, AgentResult) or r.status != "completed" or r.output is None for r in results):
            return VerificationResult(False, "challenge_verification", "result_integrity_failure")
        if tuple(r.task_id for r in results) != expected_steps:
            return VerificationResult(False, "challenge_verification", "result_step_mismatch")
        executions = tuple(r.execution_id for r in results)
        if not executions or not executions[0] or any(execution != executions[0] for execution in executions):
            return VerificationResult(False, "challenge_verification", "execution_identity_mismatch")
        if task.execution_id and executions[0] != task.execution_id:
            return VerificationResult(False, "challenge_verification", "execution_identity_mismatch")
        if final_output != results[-1].output:
            return VerificationResult(False, "challenge_verification", "final_output_mismatch")
        return VerificationResult(True, "challenge_verification", "challenge_ok")
