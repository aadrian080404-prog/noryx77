import time

from .actions import ActionGate
from .audit import AuditLog
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine
from .router import ResourceRouter


class HypersynthRuntime:
    """Fail-closed facade that owns HYPERSYNTH safety dependencies and runtime provenance."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None, clock=None,
                 runtime_id=None, provenance_key=None, model_fabric=None):
        self.audit = audit or AuditLog()
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.clock = clock or time.monotonic
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)
        self.runtime_id = runtime_id
        if provenance_key is not None and (not isinstance(provenance_key, bytes) or len(provenance_key) < 32):
            raise ValueError("provenance key must contain at least 32 bytes")
        self._provenance_key = bytes(provenance_key) if provenance_key is not None else None
        self.model_fabric = model_fabric
        if self.model_fabric is not None and self.runtime_id is not None:
            fabric_runtime_id = getattr(self.model_fabric, "runtime_id", None)
            if fabric_runtime_id != self.runtime_id:
                raise ValueError("model_fabric runtime identity mismatch")
        self.kernel = Hypersynth(
            self.verifier,
            self.router,
            planner=planner,
            action_gate=self.action_gate,
            memory=self.memory,
            audit=self.audit,
            max_steps=self.limits.max_actions_per_task,
            provenance_key=self._provenance_key,
            runtime_id=self.runtime_id or "",
            model_fabric=self.model_fabric,
        )

    def run_model(self, request, *, verifier=None, synthesizer=None):
        """Execute a Model Fabric request only inside this runtime's provenance boundary."""
        if self.model_fabric is None:
            raise RuntimeError("model_fabric_unavailable")
        runtime_id = getattr(request, "runtime_id", None)
        if not isinstance(runtime_id, str) or runtime_id != self.runtime_id:
            raise PermissionError("model request runtime identity mismatch")
        result = self.model_fabric.execute(request, verifier=verifier, synthesizer=synthesizer)
        if not self.model_fabric.verify_result(request, result):
            raise RuntimeError("model_result_integrity_failure")
        self.audit.record(
            "model_fabric_result",
            runtime_id=self.runtime_id,
            request_digest=result.request_digest,
            selected_model=result.selected_model,
            degraded=result.degraded,
        )
        return result

    def run(self, task):
        task_id = getattr(task, "task_id", None)
        started = self.clock()
        deadline = started + self.limits.max_task_seconds
        self.audit.record("hypersynth_start", task_id=task_id)

        def deadline_exceeded():
            return self.clock() > deadline

        try:
            task_check = self.verifier.verify_task(task)
            if not isinstance(task_check, VerificationResult) or not task_check.is_well_formed():
                check = VerificationResult(False, "contract", "invalid_task_verification")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            if not task_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=task_check.reason)
                return {"status": "rejected", "phase": "perception", "verification": task_check, "audit": self.audit.snapshot()}
            if deadline_exceeded():
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
            result = self.kernel.run(task, deadline_check=deadline_exceeded)
            if not isinstance(result, dict):
                check = VerificationResult(False, "runtime", "malformed_kernel_result")
                self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                return {"status": "rejected", "phase": "execution", "verification": check, "audit": self.audit.snapshot()}
            if deadline_exceeded() and result.get("status") == "completed":
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
            if result.get("status") == "completed":
                result_check = result.get("verification")
                if (not isinstance(result_check, VerificationResult) or not result_check.is_well_formed() or not result_check.valid or result_check.stage != "hypersynth_result"):
                    check = VerificationResult(False, "runtime", "invalid_kernel_verification")
                    self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
                output = result.get("results", ())
                if not isinstance(output, tuple):
                    check = VerificationResult(False, "runtime", "malformed_kernel_results")
                    self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
                if not self.limits.validate_count(len(output), self.limits.max_output_items):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
                final_output = output[-1].output if output else None
                if not self.limits.validate_output_items(final_output):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
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
