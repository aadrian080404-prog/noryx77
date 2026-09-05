from .contracts import AgentResult, TaskSpec
from .verification import VerificationEngine


class Agent:
    agent_id = "base"

    def run(self, task: TaskSpec) -> AgentResult:
        raise NotImplementedError


class DeterministicAgent(Agent):
    agent_id = "deterministic"

    def __init__(self, verifier: VerificationEngine | None = None):
        self.verifier = verifier or VerificationEngine()

    def run(self, task: TaskSpec) -> AgentResult:
        check = self.verifier.verify_task(task)
        if not check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check, execution_id=task.execution_id)
        result = AgentResult(self.agent_id, task.task_id, "completed", output=task.objective, execution_id=task.execution_id)
        output_check = self.verifier.verify_output(result.output, stage="agent_result")
        return AgentResult(self.agent_id, task.task_id, result.status, result.output, output_check, task.execution_id)


class ModelFabricAgent(Agent):
    """Adapter that binds every model invocation to one runtime identity."""
    agent_id = "model_fabric"

    def __init__(self, fabric, verifier: VerificationEngine | None = None):
        self.fabric = fabric
        self.verifier = verifier or VerificationEngine()

    def run(self, task: TaskSpec) -> AgentResult:
        check = self.verifier.verify_task(task)
        if not check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check, execution_id=task.execution_id)
        runtime_id = task.constraints.get("runtime_id")
        if runtime_id != self.fabric.runtime_id:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=VerificationResult(False, "model_fabric", "model request runtime identity mismatch"), execution_id=task.execution_id)
        required = task.constraints.get("required_capabilities", ())
        try:
            selection = self.fabric.generate(task.objective, required_capabilities=required)
            output_check = self.verifier.verify_output(selection.output, stage="agent_result")
            return AgentResult(self.agent_id, task.task_id, "completed" if output_check.valid else "rejected", selection.output, output_check, task.execution_id)
        except Exception as exc:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=VerificationResult(False, "model_fabric", type(exc).__name__), execution_id=task.execution_id)


from .contracts import VerificationResult
