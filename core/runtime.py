import time

from .actions import ActionGate
from .agents import DeterministicAgent
from .audit import AuditLog
from .contracts import ActionSpec, TaskSpec, VerificationResult
from .decomposition import TaskDecomposer
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine

class NORYXRuntime:
    """Controlled runtime: validate -> decompose -> route -> execute -> limit -> verify -> audit."""

    def __init__(self, limits: RuntimeLimits | None = None):
        self.limits = limits or RuntimeLimits()
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = MemoryStore(max_items=self.limits.max_memory_items)
        self.audit = AuditLog()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.decomposer = TaskDecomposer()
        self.hypersynth = HypersynthRuntime(
            verifier=self.verifier,
            router=self.router,
            audit=self.audit,
            limits=self.limits,
            memory=self.memory,
        )

    def run(self, task: TaskSpec, agent_id: str = "deterministic"):
        started = time.monotonic()
        deadline = started + self.limits.max_task_seconds
        task_id = getattr(task, "task_id", None)

        def deadline_exceeded() -> bool:
            return time.monotonic() > deadline

        try:
            task_check = self.verifier.verify_task(task)
        except Exception:
            self.audit.record("task_verification_failure", task_id=task_id, reason="controlled_runtime_failure")
            return {"status": "rejected", "reason": "controlled_runtime_failure", "task_id": task_id}
        self.audit.record("task_verification", task_id=task_id, valid=task_check.valid, reason=task_check.reason)
        if not task_check.valid:
            return {"status": "rejected", "reason": task_check.reason, "verification": task_check}

        if not self.limits.validate_input(task.input):
            result = {"status": "rejected", "reason": "input_limit_exceeded"}
            self.audit.record("task_rejected", task_id=task_id, reason=result["reason"])
            return result
        if deadline_exceeded():
            self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
            return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}

        try:
            subtasks = self.decomposer.decompose(task)
            agent = self.router.route(agent_id)
        except Exception:
            self.audit.record("routing_failure", task_id=task_id, error="routing_failure")
            return {"status": "rejected", "reason": "routing_failure"}

        if len(subtasks) > self.limits.max_actions_per_task:
            self.audit.record("action_limit", task_id=task_id, allowed=False, reason="max_actions_per_task_exceeded")
            return {"status": "rejected", "reason": "max_actions_per_task_exceeded", "task_id": task_id}

        results = []
        for subtask in subtasks:
            if deadline_exceeded():
                self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
                return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}
            child = TaskSpec(subtask.subtask_id, subtask.task_type, subtask.objective, task.input,
                             task.constraints, task.verification_requirements, task.risk_class)
            action = ActionSpec("act:" + child.task_id, "compute", risk_class=child.risk_class)
            decision = self.action_gate.authorize(action, calls_used=len(results))
            self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
            if not decision.allowed:
                return {"status": "rejected", "verification": decision.verification}

            try:
                result = agent.run(child)
                output = result.output
            except Exception as exc:
                self.audit.record("execution_failure", task_id=child.task_id, error=type(exc).__name__, reason="agent_execution_failure")
                check = VerificationResult(False, "execution", "agent_execution_failure")
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}

            if deadline_exceeded():
                self.audit.record("task_timeout", task_id=child.task_id, reason="max_task_seconds_exceeded")
                return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": child.task_id}
            if not self.limits.validate_output(output):
                self.audit.record("output_limit", task_id=child.task_id, allowed=False, reason="output_limit_exceeded")
                return {"status": "rejected", "reason": "output_limit_exceeded", "task_id": child.task_id}
            if not self.limits.validate_output_items(output):
                self.audit.record("output_item_limit", task_id=child.task_id, allowed=False, reason="max_output_items_exceeded")
                return {"status": "rejected", "reason": "max_output_items_exceeded", "task_id": child.task_id}

            runtime_verification = self.verifier.verify_output(output, stage="runtime_result")
            self.audit.record(
                "runtime_output_verification",
                task_id=child.task_id,
                valid=runtime_verification.valid,
                reason=runtime_verification.reason,
            )
            if not runtime_verification.valid:
                return {"status": "rejected", "reason": "runtime_output_verification_failed", "verification": runtime_verification, "task_id": child.task_id}
            if result.verification is None or not result.verification.valid:
                return {"status": "rejected", "result": result}

            results.append(result)
            self.audit.record("agent_result", task_id=child.task_id, agent_id=agent.agent_id, status=result.status)

        if deadline_exceeded():
            self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
            return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}
        return {"status": "completed", "results": tuple(results), "audit": self.audit.snapshot()}

    def run_hypersynth(self, task: TaskSpec):
        """Execute a task through the bounded HYPERSYNTH cognitive pipeline."""
        return self.hypersynth.run(task)
