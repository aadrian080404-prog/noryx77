from .actions import ActionGate
from .audit import AuditLog
from .contracts import VerificationResult
from .hypersynth import Hypersynth
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine
from .router import ResourceRouter


class HypersynthRuntime:
    """Fail-closed facade that owns HYPERSYNTH safety dependencies and runtime limits."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None):
        self.audit = audit or AuditLog()
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = memory or MemoryStore()
        self.kernel = Hypersynth(
            self.verifier,
            self.router,
            planner=planner,
            action_gate=self.action_gate,
            memory=self.memory,
            audit=self.audit,
        )

    def run(self, task):
        task_id = getattr(task, "task_id", None)
        self.audit.record("hypersynth_start", task_id=task_id)
        try:
            if not self.limits.validate_input(getattr(task, "input", None)):
                check = VerificationResult(False, "limits", "input_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status": "rejected", "phase": "perception", "verification": check, "audit": self.audit.snapshot()}
            result = self.kernel.run(task)
        except Exception as exc:
            self.audit.record("hypersynth_failure", task_id=task_id, error=type(exc).__name__)
            return {
                "status": "rejected",
                "phase": "execution",
                "reason": "controlled_runtime_failure",
                "audit": self.audit.snapshot(),
            }
        result["audit"] = self.audit.snapshot()
        return result
