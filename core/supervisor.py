from dataclasses import dataclass
from hashlib import sha256
from .contracts import TaskSpec, AgentResult, VerificationResult
from .identity import AgentIdentity


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
        try:
            check = self.verifier.verify_task(task)
        except Exception:
            return None, AgentDecision("", False, "task_verification_failure")
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid:
            reason = check.reason if isinstance(check, VerificationResult) and check.is_well_formed() else "invalid_task_verification"
            return None, AgentDecision("", False, reason)
        agent_id = ""
        try:
            agent_id = preferred or self.router.default_id()
            required_capability = "execute" if getattr(self.router, "system_fabric", None) is not None else None
            if required_capability is None:
                agent = self.router.route(agent_id)
            else:
                agent = self.router.route(agent_id, required_capability=required_capability)
        except LookupError as exc:
            if "agent_identity_untrusted" in str(exc):
                return None, AgentDecision(agent_id, False, "agent_identity_untrusted")
            return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_selection_failure")
        except PermissionError as exc:
            reason = str(exc) or "agent_execution_not_authorized"
            if reason in {"authorization_not_valid", "capability_not_granted", "agent_identity_not_trusted", "canonical_system_fabric_required"}:
                return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_execution_not_authorized")
            if reason in {"agent_identity_required", "agent_identity_untrusted"}:
                return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_identity_mismatch")
            return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_selection_failure")
        except Exception:
            return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_selection_failure")
        if agent is None:
            return None, AgentDecision(agent_id, False, "agent_unavailable")
        if not isinstance(agent_id, str) or not agent_id or getattr(agent, "agent_id", None) != agent_id:
            return None, AgentDecision(agent_id if isinstance(agent_id, str) else "", False, "agent_identity_mismatch")
        registry = getattr(self.router, "identity_registry", None)
        if registry is not None:
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or identity.agent_id != agent_id or not registry.is_trusted(identity):
                return None, AgentDecision(agent_id, False, "agent_identity_untrusted")
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
        if not isinstance(result.agent_id, str) or not result.agent_id.strip():
            return VerificationResult(False, "agent_result", "agent_identity_mismatch")
        if task.execution_id and result.execution_id != task.execution_id:
            return VerificationResult(False, "agent_result", "execution_identity_mismatch")
        agent = self.router.get(result.agent_id)
        if agent is None:
            return VerificationResult(False, "agent_result", "agent_unavailable")
        if getattr(agent, "agent_id", None) != result.agent_id:
            return VerificationResult(False, "agent_result", "agent_identity_mismatch")
        registry = getattr(self.router, "identity_registry", None)
        if registry is not None:
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or identity.agent_id != result.agent_id or not registry.is_trusted(identity):
                return VerificationResult(False, "agent_result", "agent_identity_untrusted")
            expected_fingerprint = sha256(identity.public_key).hexdigest()
            if selected_agent_id is not None and result.agent_key_fingerprint != expected_fingerprint:
                return VerificationResult(False, "agent_result", "agent_attestation_identity_mismatch")
        if result.task_id != task.task_id:
            return VerificationResult(False, "agent_result", "task_id_mismatch")
        if result.status != "completed":
            return VerificationResult(False, "agent_result", "agent_not_completed")
        try:
            output_check = self.verifier.verify_output(result.output, stage="agent_result")
        except Exception:
            return VerificationResult(False, "agent_result", "verification_failure")
        if not isinstance(output_check, VerificationResult) or not output_check.is_well_formed():
            return VerificationResult(False, "agent_result", "invalid_output_verification")
        if not output_check.valid:
            return output_check
        if output_check.stage != "agent_result":
            return VerificationResult(False, "agent_result", "verification_stage_mismatch")
        if result.verification is None:
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.valid:
            return VerificationResult(False, "agent_result", "result_verification_failed")
        if result.verification.stage != "agent_result":
            return VerificationResult(False, "agent_result", "verification_stage_mismatch")
        return VerificationResult(True, "agent_result", "agent_result_ok")
