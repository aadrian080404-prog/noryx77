from dataclasses import dataclass
from .contracts import TaskSpec, AgentResult, VerificationResult


@dataclass(frozen=True)
class AgentDecision:
    agent_id: str
    accepted: bool
    reason: str


class AgentSupervisor:
    """Supervises agent selection and result admission; it never bypasses verification."""
    def __init__(self, router, verifier, audit=None):
        self.router = router
        self.verifier = verifier
        self.audit = audit

    def select(self, task: TaskSpec, preferred=None):
        check = self.verifier.verify_task(task)
        if not check.valid:
            return None, AgentDecision("", False, check.reason)
        agent_id = preferred or self.router.default_id()
        agent = self.router.route(agent_id)
        if agent is None:
            return None, AgentDecision(agent_id, False, "agent_unavailable")
        decision = AgentDecision(agent_id, True, "agent_selected")
        if self.audit:
            self.audit.record("agent_selection", task_id=task.task_id, agent_id=agent_id, accepted=True)
        return agent, decision

    def admit(self, task: TaskSpec, result: AgentResult, *, selected_agent_id: str | None = None):
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "agent_result", "invalid_task_contract")
        if not isinstance(result, AgentResult):
            return VerificationResult(False, "agent_result", "invalid_agent_result")
        if not result.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_agent_result")
        if selected_agent_id is not None and result.agent_id != selected_agent_id:
            return VerificationResult(False, "agent_result", "agent_identity_mismatch")
        if result.task_id != task.task_id:
            return VerificationResult(False, "agent_result", "task_id_mismatch")
        if result.status != "completed":
            return VerificationResult(False, "agent_result", "agent_not_completed")
        output_check = self.verifier.verify_output(result.output, stage="agent_result")
        if not output_check.valid:
            return output_check
        if result.verification is None:
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.valid:
            return VerificationResult(False, "agent_result", "result_verification_failed")
        if result.verification.stage != "agent_result":
            return VerificationResult(False, "agent_result", "verification_stage_mismatch")
        return VerificationResult(True, "agent_result", "agent_result_ok")
