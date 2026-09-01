from dataclasses import dataclass
from .contracts import TaskSpec, AgentResult, VerificationResult
from .validation_requirements import VALID_VERIFICATION_REQUIREMENTS


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

    @staticmethod
    def _checked_task_verification(check):
        if not isinstance(check, VerificationResult) or not check.is_well_formed():
            return VerificationResult(False, "contract", "malformed_task_verification")
        if check.stage != "contract":
            return VerificationResult(False, "contract", "task_verification_stage_mismatch")
        if not check.valid:
            return check
        return check

    def select(self, task: TaskSpec, preferred=None):
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return None, AgentDecision("", False, "invalid_task_contract")
        if task.risk_class not in {"normal", "sensitive", "high"}:
            return None, AgentDecision("", False, "unsupported_risk_class")
        if any(requirement not in VALID_VERIFICATION_REQUIREMENTS for requirement in task.verification_requirements):
            return None, AgentDecision("", False, "unsupported_verification_requirement")
        try:
            check = self.verifier.verify_task(task)
        except Exception:
            return None, AgentDecision("", False, "verifier_task_failure")
        check = self._checked_task_verification(check)
        if not check.valid:
            return None, AgentDecision("", False, check.reason)
        agent_id = preferred or self.router.default_id()
        if not isinstance(agent_id, str) or not agent_id.strip():
            return None, AgentDecision("", False, "invalid_agent_id")
        try:
            agent = self.router.route(agent_id)
        except Exception:
            return None, AgentDecision(agent_id, False, "agent_route_failure")
        if agent is None:
            return None, AgentDecision(agent_id, False, "agent_unavailable")
        if getattr(agent, "agent_id", None) != agent_id:
            return None, AgentDecision(agent_id, False, "agent_identity_mismatch")
        decision = AgentDecision(agent_id, True, "agent_selected")
        if self.audit:
            self.audit.record("agent_selection", task_id=task.task_id, agent_id=agent_id, accepted=True)
        return agent, decision

    def admit(self, task: TaskSpec, result: AgentResult):
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return VerificationResult(False, "agent_result", "invalid_task_contract")
        if task.risk_class not in {"normal", "sensitive", "high"}:
            return VerificationResult(False, "agent_result", "unsupported_risk_class")
        if any(requirement not in VALID_VERIFICATION_REQUIREMENTS for requirement in task.verification_requirements):
            return VerificationResult(False, "agent_result", "unsupported_verification_requirement")
        if not isinstance(result, AgentResult):
            return VerificationResult(False, "agent_result", "invalid_agent_result")
        if not result.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_agent_result")
        if result.task_id != task.task_id:
            return VerificationResult(False, "agent_result", "task_id_mismatch")
        if result.status != "completed":
            return VerificationResult(False, "agent_result", "agent_not_completed")
        try:
            output_check = self.verifier.verify_output(result.output, requirements=task.verification_requirements, stage="agent_result")
        except Exception:
            return VerificationResult(False, "agent_result", "verifier_output_failure")
        if not isinstance(output_check, VerificationResult) or not output_check.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_output_verification")
        if output_check.stage != "agent_result":
            return VerificationResult(False, "agent_result", "output_verification_stage_mismatch")
        if not output_check.valid:
            return output_check
        if result.verification is None:
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.valid:
            return VerificationResult(False, "agent_result", "result_verification_failed")
        return VerificationResult(True, "agent_result", "agent_result_ok")
