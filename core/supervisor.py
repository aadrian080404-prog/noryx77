from dataclasses import dataclass
from .contracts import TaskSpec, AgentResult, VerificationResult
from .validation_requirements import VALID_VERIFICATION_REQUIREMENTS
from .routing_policy import MODEL_ORDER, TASK_MODEL_HINTS


@dataclass(frozen=True)
class AgentDecision:
    agent_id: str
    accepted: bool
    reason: str


class AgentSupervisor:
    """Supervises agent selection and result admission; it never bypasses verification."""
    MODEL_ORDER = MODEL_ORDER
    TASK_MODEL_HINTS = TASK_MODEL_HINTS

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

    def _resource_eligibility(self, task: TaskSpec, agent) -> VerificationResult:
        # Capacity enforcement applies only when the agent explicitly publishes
        # routing metadata on the instance. This preserves the pre-routing
        # compatibility contract for legacy agents while keeping explicit model
        # declarations enforceable and fail-closed.
        explicit_model = isinstance(getattr(agent, "__dict__", None), dict) and "model_class" in agent.__dict__
        model_class = getattr(agent, "model_class", "medium")
        if not isinstance(model_class, str) or model_class not in self.MODEL_ORDER:
            return VerificationResult(False, "allocation", "invalid_model_class")
        if getattr(agent, "capacity_exempt", False) is True or not explicit_model:
            return VerificationResult(True, "allocation", "resource_legacy_eligible")
        required = self.TASK_MODEL_HINTS.get(task.task_type, "medium")
        if self.MODEL_ORDER.index(model_class) < self.MODEL_ORDER.index(required):
            return VerificationResult(False, "allocation", "resource_underpowered_for_task")
        return VerificationResult(True, "allocation", "resource_task_eligible")

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

        # Explicit preferences are strict and are never silently replaced.
        # Without a preference, delegate task-aware choice to ResourceRouter so
        # the supervisor and router share one authoritative routing decision.
        if preferred is not None:
            if not isinstance(preferred, str) or not preferred.strip():
                return None, AgentDecision("", False, "invalid_preferred_agent_id")
            agent_id = preferred
            try:
                agent = self.router.route(agent_id)
            except Exception:
                return None, AgentDecision(agent_id, False, "agent_route_failure")
        else:
            try:
                agent = self.router.route_for_task(task)
            except LookupError:
                return None, AgentDecision("", False, "no_resource_satisfies_task")
            except Exception:
                return None, AgentDecision("", False, "agent_route_failure")
            agent_id = getattr(agent, "agent_id", None)

        if not isinstance(agent_id, str) or not agent_id.strip():
            return None, AgentDecision("", False, "invalid_agent_id")
        if agent is None:
            return None, AgentDecision(agent_id, False, "agent_unavailable")
        if getattr(agent, "agent_id", None) != agent_id:
            return None, AgentDecision(agent_id, False, "agent_identity_mismatch")
        eligibility = self._resource_eligibility(task, agent)
        if not eligibility.valid:
            return None, AgentDecision(agent_id, False, eligibility.reason)
        decision = AgentDecision(agent_id, True, "agent_selected")
        if self.audit:
            self.audit.record("agent_selection", task_id=task.task_id, agent_id=agent_id, accepted=True, model_class=getattr(agent, "model_class", "medium"))
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
