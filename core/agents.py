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
