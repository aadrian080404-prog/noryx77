import hashlib
import time

from .actions import ActionGate
from .audit import AuditLog
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .interaction_context import InteractionContext
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .recovery import RecoveryController, RecoveryState
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine


class HypersynthRuntime:
    """Fail-closed facade owning HYPERSYNTH safety dependencies and context."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None, clock=None, recovery=None):
        self.audit = audit or AuditLog()
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.clock = clock or time.monotonic
        self.policy = PolicyEngine()
        self.recovery = recovery or RecoveryController()
        if not isinstance(self.recovery, RecoveryController):
            raise TypeError("invalid_recovery_controller")
        self.identity_registry = getattr(self.router, "identity_registry", None)
        if self.identity_registry is None:
            raise ValueError("hypersynth_identity_registry_required")
        self.security = SecurityBoundary(self.policy, self.verifier, self.recovery)
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
            recovery=self.recovery,
        )

    def _principal_binding(self, agent_ids):
        """Require every execution participant to be a currently trusted agent identity."""
        bindings = []
        for agent_id in tuple(agent_ids):
            agent = self.router.route(agent_id)
            identity = getattr(agent, "identity", None)
            if not self.identity_registry.is_trusted(identity):
                raise PermissionError("agent_identity_untrusted")
            bindings.append((identity.agent_id, hashlib.sha256(identity.public_key).hexdigest()))
        if not bindings:
            raise PermissionError("no_trusted_hypersynth_agent")
        return tuple(bindings)

    def run(self, task: TaskSpec, *, interaction_context: InteractionContext):
        task_id = getattr(task, "task_id", None)
        started = self.clock()
        deadline = started + self.limits.max_task_seconds
        recovery_state, recovery_epoch = self.recovery.snapshot()
        self.audit.record("hypersynth_start", task_id=task_id, context_id=getattr(interaction_context, "context_id", None))

        def deadline_exceeded():
            return self.clock() > deadline

        if recovery_state is not RecoveryState.NORMAL:
            check = VerificationResult(False, "recovery", "recovery_state_denies_execution")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="recovery", reason=check.reason)
            return {"status": "rejected", "phase": "recovery", "verification": check, "audit": self.audit.snapshot()}

        if not isinstance(interaction_context, InteractionContext):
            check = VerificationResult(False, "context", "interaction_context_required")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="context", reason=check.reason)
            return {"status": "rejected", "phase": "context", "verification": check, "audit": self.audit.snapshot()}
        try:
            interaction_context.as_prompt_context()
        except (TypeError, ValueError):
            check = VerificationResult(False, "context", "invalid_interaction_context")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="context", reason=check.reason)
            return {"status": "rejected", "phase": "context", "verification": check, "audit": self.audit.snapshot()}

        try:
            self.recovery.require_normal(expected_epoch=recovery_epoch)
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
            self.audit.record("hypersynth_context_bound", task_id=task_id, context_id=interaction_context.context_id)
            # The kernel may select multiple agents. Validate the complete registered route set
            # before entering cognition so an untrusted route can never become an execution path.
            principal_bindings = self._principal_binding(self.router.available())
            self.audit.record("hypersynth_identity_bound", task_id=task_id, principals=tuple(x[0] for x in principal_bindings),
                              fingerprints=tuple(x[1] for x in principal_bindings))
            result = self.kernel.run(task, deadline_check=deadline_exceeded)
            if not isinstance(result, dict):
                check = VerificationResult(False, "runtime", "malformed_kernel_result")
                self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                return {"status": "rejected", "phase": "execution", "verification": check, "audit": self.audit.snapshot()}
            if deadline_exceeded() and result.get("status") == "completed":
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                return {"status": "rejected", "phase": "verification", "verification": check, "audit": self.audit.snapshot()}
            self.recovery.require_normal(expected_epoch=recovery_epoch)
            if result.get("status") == "completed":
                result_check = result.get("verification")
                if (not isinstance(result_check, VerificationResult) or not result_check.is_well_formed()
                        or not result_check.valid or result_check.stage != "hypersynth_result"):
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
        except PermissionError as exc:
            check = VerificationResult(False, "identity", str(exc))
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="identity", reason=check.reason)
            return {"status": "rejected", "phase": "identity", "verification": check, "audit": self.audit.snapshot()}
        except Exception:
            check = VerificationResult(False, "runtime", "controlled_runtime_failure")
            self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
            return {"status": "rejected", "phase": "execution", "reason": check.reason, "verification": check, "audit": self.audit.snapshot()}
        result["audit"] = self.audit.snapshot()
        return result
