from .contracts import TaskSpec
from .audit import AuditLog
from .hypersynth import Hypersynth

class HypersynthRuntime:
    """Public facade around the cognitive kernel with audit and fail-closed handling."""
    def __init__(self, verifier, router, planner=None, audit=None):
        self.audit = audit or AuditLog()
        self.kernel = Hypersynth(verifier, router, planner=planner)

    def run(self, task: TaskSpec):
        self.audit.record("hypersynth_start", task_id=task.task_id)
        try:
            result = self.kernel.run(task)
        except Exception as exc:
            self.audit.record("hypersynth_failure", task_id=task.task_id, error=type(exc).__name__)
            return {"status": "rejected", "phase": "execution", "reason": "controlled_runtime_failure", "audit": self.audit.snapshot()}
        self.audit.record("hypersynth_complete", task_id=task.task_id, status=result.get("status"))
        result["audit"] = self.audit.snapshot()
        return result
