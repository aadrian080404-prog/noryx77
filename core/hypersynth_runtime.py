import math
import time

from .actions import ActionGate
from .agents import DeterministicAgent, ProviderAgent
from .audit import AuditLog
from .contracts import AgentResult, TaskSpec, VerificationResult
from .crypto import CryptoIntegrity
from .decomposition import TaskDecomposer
from .hypersynth import Hypersynth
from .hypersynth_kernel import AttestedHypersynthKernel
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .security import SecurityBoundary
from .security_lockdown import SecurityLockdown
from .verification import VerificationEngine
from .router import ResourceRouter


class HypersynthRuntime:
    """Fail-closed facade that owns HYPERSYNTH execution, integrity, and runtime limits."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None, clock=None, provider: Provider | None = None, agent_id: str = "provider", provider_model_class: str = "large", provider_capabilities: tuple[str, ...] = (), admin_authorizer=None, lockdown=None):
        self.audit = audit or AuditLog()
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.clock = clock or time.monotonic
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.crypto = CryptoIntegrity()
        if lockdown is not None and not isinstance(lockdown, SecurityLockdown):
            raise TypeError("invalid_security_lockdown")
        self.security_lockdown = lockdown or SecurityLockdown(
            self.crypto,
            admin_authorizer if admin_authorizer is not None else (lambda proof: False),
        )
        self.action_gate = ActionGate(self.policy, self.security, self.limits, crypto=self.crypto, lockdown=self.security_lockdown)
        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)
        if provider is not None:
            self.router.register(ProviderAgent(agent_id, provider, self.verifier, model_class=provider_model_class, capabilities=provider_capabilities))
        elif not self.router.available():
            self.router.register(DeterministicAgent(self.verifier))
        self.kernel = Hypersynth(
            self.verifier,
            self.router,
            planner=planner,
            action_gate=self.action_gate,
            memory=self.memory,
            audit=self.audit,
            max_steps=self.limits.max_actions_per_task,
        )
        # The runtime boundary exposes only the attested kernel. This keeps the
        # nine-stage execution result cryptographically bound to the run before
        # it leaves the runtime-owned admission checks below.
        self.attested_kernel = AttestedHypersynthKernel(self.kernel)

    def _read_clock(self):
        """Read a finite monotonic timestamp; malformed or regressing clocks fail closed."""
        if not callable(self.clock):
            raise TypeError("invalid_runtime_clock")
        value = self.clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("invalid_runtime_clock_value")
        if not math.isfinite(value):
            raise ValueError("non_finite_runtime_clock")
        return value

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
            if not isinstance(result.get("phase"), str) or not result["phase"].strip():
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
        try:
            expected_subtasks = TaskDecomposer().decompose(task)
            expected_task_ids = tuple(item.subtask_id for item in expected_subtasks)
        except Exception:
            return VerificationResult(False, "runtime", "runtime_decomposition_failure")
        if len(results) != len(expected_task_ids):
            return VerificationResult(False, "runtime", "kernel_result_count_mismatch")
        task_ids = []
        agent_ids = []
        for index, item in enumerate(results):
            if not isinstance(item, AgentResult) or not item.is_well_formed():
                return VerificationResult(False, "runtime", "malformed_kernel_agent_result")
            if item.status != "completed":
                return VerificationResult(False, "runtime", "incomplete_kernel_agent_result")
            if item.verification is None or not item.verification.is_well_formed() or not item.verification.valid:
                return VerificationResult(False, "runtime", "unverified_kernel_agent_result")
            if item.task_id != expected_task_ids[index]:
                return VerificationResult(False, "runtime", "kernel_result_task_identity_mismatch")
            task_ids.append(item.task_id)
            agent_ids.append(item.agent_id)
        if len(set(task_ids)) != len(task_ids):
            return VerificationResult(False, "runtime", "duplicate_kernel_result_task_id")
        if len(set(agent_ids)) != len(agent_ids):
            return VerificationResult(False, "runtime", "duplicate_kernel_result_agent_id")
        attestations = result.get("attestations")
        if not isinstance(attestations, tuple) or len(attestations) != len(AttestedHypersynthKernel.STAGE_ORDER):
            return VerificationResult(False, "runtime", "missing_kernel_attestations")
        if tuple(getattr(item, "stage", None) for item in attestations) != AttestedHypersynthKernel.STAGE_ORDER:
            return VerificationResult(False, "runtime", "kernel_attestation_stage_order_mismatch")
        if result.get("attestation_verified") is not True or result.get("final_integrity_verified") is not True:
            return VerificationResult(False, "runtime", "kernel_integrity_not_verified")
        if result.get("export_manifest_verified") is not True or result.get("continuity_verified") is not True:
            return VerificationResult(False, "runtime", "kernel_export_integrity_not_verified")
        return VerificationResult(True, "runtime", "kernel_completion_contract_ok")

    def run(self, task):
        task_id = getattr(task, "task_id", None)
        try:
            if not self.security_lockdown.permits():
                check = VerificationResult(False, "runtime", "global_lockdown")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="security", reason=check.reason)
                return {"status": "rejected", "phase": "security", "verification": check, "audit": self.audit.snapshot()}
            started = self._read_clock()
            self.audit.record("hypersynth_start", task_id=task_id)
            task_check = self.verifier.verify_task(task)
            if not isinstance(task_check, VerificationResult) or not task_check.is_well_formed():
                check = VerificationResult(False, "runtime", "malformed_task_verification")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            if not task_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=task_check.reason)
                return {"status": "rejected", "phase": "perception", "verification": task_check, "audit": self.audit.snapshot()}
            elapsed = self._read_clock() - started
            if elapsed < 0 or elapsed > self.limits.max_task_seconds:
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
            result = self.attested_kernel.run(task)
            kernel_check = self._independent_kernel_result_contract(task, result)
            if not kernel_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=kernel_check.reason)
                return {"status": "rejected", "phase":"verification", "verification": kernel_check, "audit": self.audit.snapshot()}
            elapsed = self._read_clock() - started
            if elapsed < 0 or elapsed > self.limits.max_task_seconds:
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                return {"status": "rejected", "phase":"verification", "verification": check, "audit": self.audit.snapshot()}
            output = result.get("results", ())
            if result.get("status") == "completed":
                if not self.limits.validate_count(len(output), self.limits.max_output_items):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase":"verification", "verification": check, "audit": self.audit.snapshot()}
                final_output = output[-1].output if output else None
                if not self.limits.validate_output(final_output):
                    check = VerificationResult(False, "limits", "output_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase":"verification", "verification": check, "audit": self.audit.snapshot()}
        except Exception:
            check = VerificationResult(False, "runtime", "controlled_runtime_failure")
            self.audit.record("hypersynth_failure", task_id=task_id, error="runtime_exception", reason=check.reason)
            return {"status": "rejected", "phase": "execution", "reason": check.reason, "verification": check, "audit": self.audit.snapshot()}
        result["audit"] = self.audit.snapshot()
        return result
