import time

from .actions import ActionGate
from .audit import AuditLog
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine
from .router import ResourceRouter


class HypersynthRuntime:
    """Fail-closed facade that owns HYPERSYNTH safety dependencies and runtime limits."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None, clock=None):
        self.audit = audit or AuditLog()
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.clock = clock or time.monotonic
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)
        self.kernel = Hypersynth(
            self.verifier,
            self.router,
            planner=planner,
            action_gate=self.action_gate,
            memory=self.memory,
            audit=self.audit,
            max_steps=self.limits.max_actions_per_task,
        )

    @staticmethod
    def _independent_kernel_result_contract(task: TaskSpec, result) -> VerificationResult:
        """Runtime-owned admission gate; an injected kernel cannot forge a successful envelope."""
        if not isinstance(result, dict):
            return VerificationResult(False, "runtime", "malformed_kernel_result")
        status = result.get("status")
        verification = result.get("verification")
        if not isinstance(verification, VerificationResult) or not verification.is_well_formed():
            return VerificationResult(False, "runtime", "malformed_kernel_verification")
        if status == "rejected":
            if verification.valid:
                return VerificationResult(False, "runtime", "rejected_result_claims_success")
            if result.get("phase") is None:
                return VerificationResult(False, "runtime", "rejected_result_missing_phase")
            return VerificationResult(True, "runtime", "kernel_rejection_contract_ok")
        if status != "completed":
            return VerificationResult(False, "runtime", "invalid_kernel_status")
        if not verification.valid or verification.stage != "hypersynth_result":
            return VerificationResult(False, "runtime", "invalid_kernel_completion_verification")
        if result.get("phase") != "metacognition":
            return VerificationResult(False, "runtime", "invalid_kernel_completion_phase")
        state = result.get("state")
        if getattr(state, "task_id", None) != task.task_id or getattr(state, "phase", None) != "metacognition":
            return VerificationResult(False, "runtime", "kernel_state_identity_mismatch")
        results = result.get("results")
        if not isinstance(results, tuple) or not results:
            return VerificationResult(False, "runtime", "invalid_kernel_results")
        task_ids = []
        agent_ids = []
        for item in results:
            if not isinstance(item, AgentResult) or not item.is_well_formed():
                return VerificationResult(False, "runtime", "malformed_kernel_agent_result")
            if item.status != "completed":
                return VerificationResult(False, "runtime", "incomplete_kernel_agent_result")
            if item.verification is None or not item.verification.is_well_formed() or not item.verification.valid:
                return VerificationResult(False, "runtime", "unverified_kernel_agent_result")
            if not item.task_id.startswith(task.task_id + ":"):
                return VerificationResult(False, "runtime", "kernel_result_task_identity_mismatch")
            task_ids.append(item.task_id)
            agent_ids.append(item.agent_id)
        if len(set(task_ids)) != len(task_ids):
            return VerificationResult(False, "runtime", "duplicate_kernel_result_task_id")
        if len(set(agent_ids)) != len(agent_ids):
            return VerificationResult(False, "runtime", "duplicate_kernel_result_agent_id")
        return VerificationResult(True, "runtime", "kernel_completion_contract_ok")

    def run(self, task):
        task_id = getattr(task, "task_id", None)
        started = self.clock()
        self.audit.record("hypersynth_start", task_id=task_id)
        try:
            # Validate the public runtime contract before touching task fields.
            task_check = self.verifier.verify_task(task)
            if not isinstance(task_check, VerificationResult) or not task_check.is_well_formed():
                check = VerificationResult(False, "runtime", "malformed_task_verification")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            if not task_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=task_check.reason)
                return {"status": "rejected", "phase": "perception", "verification": task_check, "audit": self.audit.snapshot()}
            if self.clock() - started > self.limits.max_task_seconds:
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            if not self.limits.validate_input(task.input):
                check = VerificationResult(False, "limits", "input_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            if not self.limits.validate_input(task.objective):
                check = VerificationResult(False, "limits", "objective_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            result = self.kernel.run(task)
            kernel_check = self._independent_kernel_result_contract(task, result)
            if not kernel_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=kernel_check.reason)
                return {"status": "rejected", "phase": "verification", "verification": kernel_check, "audit": self.audit.snapshot()}
            if self.clock() - started > self.limits.max_task_seconds:
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
            output = result.get("results", ())
            if result.get("status") == "completed":
                if not self.limits.validate_count(len(output), self.limits.max_output_items):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
                final_output = output[-1].output if output else None
                if not self.limits.validate_output(final_output):
                    check = VerificationResult(False, "limits", "output_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
        except Exception as exc:
            check = VerificationResult(False, "runtime", "controlled_runtime_failure")
            self.audit.record("hypersynth_failure", task_id=task_id, error=type(exc).__name__, reason=check.reason)
            return {"status": "rejected", "phase": "execution", "reason": check.reason, "verification": check, "audit": self.audit.snapshot()}
        result["audit"] = self.audit.snapshot()
        return result