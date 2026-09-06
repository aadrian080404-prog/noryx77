from .contracts import AgentResult, TaskSpec, VerificationResult
from .verification import VerificationEngine
from noryx7_runtime.model_fabric import ModelFabric, ModelRequest


class Agent:
    agent_id = "base"

    def __init__(self, agent_id: str | None = None):
        if agent_id is not None:
            if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id.encode("utf-8")) > 256:
                raise ValueError("invalid agent_id")
            self.agent_id = agent_id

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
    """HYPERSYNTH execution adapter backed by the runtime-bound Model Fabric."""
    agent_id = "model_fabric"

    def __init__(self, fabric: ModelFabric, verifier: VerificationEngine | None = None):
        if not isinstance(fabric, ModelFabric):
            raise ValueError("invalid_model_fabric")
        self.fabric = fabric
        self.verifier = verifier or VerificationEngine()

    def run(self, task: TaskSpec) -> AgentResult:
        check = self.verifier.verify_task(task)
        if not check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check, execution_id=task.execution_id)
        constraints = task.constraints
        runtime_id = constraints.get("runtime_id", "") if hasattr(constraints, "get") else ""
        if not isinstance(runtime_id, str) or runtime_id != self.fabric.runtime_id:
            failure = VerificationResult(False, "model_fabric", "model request runtime identity mismatch")
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=failure, execution_id=task.execution_id)
        required = constraints.get("required_capabilities", ()) if hasattr(constraints, "get") else ()
        preferred = constraints.get("preferred_capabilities", ()) if hasattr(constraints, "get") else ()
        tools = constraints.get("tools", ()) if hasattr(constraints, "get") else ()
        try:
            request = ModelRequest(
                prompt=task.objective,
                required_capabilities=frozenset(required),
                preferred_capabilities=frozenset(preferred),
                max_cost=constraints.get("max_model_cost") if hasattr(constraints, "get") else None,
                max_latency_ms=constraints.get("max_model_latency_ms") if hasattr(constraints, "get") else None,
                min_models=int(constraints.get("min_models", 1)) if hasattr(constraints, "get") else 1,
                max_models=int(constraints.get("max_models", 3)) if hasattr(constraints, "get") else 3,
                tools=tuple(tools),
                runtime_id=runtime_id,
            )
            result = self.fabric.execute(request)
            if not self.fabric.verify_result(request, result):
                failure = VerificationResult(False, "model_fabric", "model_result_integrity_failure")
                return AgentResult(self.agent_id, task.task_id, "rejected", verification=failure, execution_id=task.execution_id)
        except Exception as exc:
            failure = VerificationResult(False, "model_fabric", type(exc).__name__)
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=failure, execution_id=task.execution_id)
        output_check = self.verifier.verify_output(result.output, stage="agent_result")
        if not output_check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", result.output, output_check, task.execution_id)
        return AgentResult(self.agent_id, task.task_id, "completed", result.output, output_check, task.execution_id)
