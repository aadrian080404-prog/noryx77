from .agents import DeterministicAgent
from .contracts import TaskSpec
from .memory import MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .verification import VerificationEngine
from .audit import AuditLog

class NORYXRuntime:
    """Controlled foundation runtime: task -> route -> execute -> verify -> audit."""
    def __init__(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.memory = MemoryStore()
        self.audit = AuditLog()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))

    def run(self, task: TaskSpec, agent_id: str = "deterministic"):
        task_check = self.verifier.verify_task(task)
        self.audit.record("task_verification", task_id=task.task_id, valid=task_check.valid, reason=task_check.reason)
        if not task_check.valid:
            return {"status": "rejected", "verification": task_check}
        agent = self.router.route(agent_id)
        result = agent.run(task)
        self.audit.record("agent_result", task_id=task.task_id, agent_id=agent.agent_id, status=result.status)
        if result.verification is None or not result.verification.valid:
            return {"status": "rejected", "result": result}
        return {"status": "completed", "result": result, "audit": self.audit.snapshot()}
