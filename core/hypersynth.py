from dataclasses import dataclass
from typing import Any

from .contracts import TaskSpec, VerificationResult
from .planning import Planner
from .coordination import AgentCoordinator

@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0

class Hypersynth:
    """Controlled cognitive kernel: perceive -> plan -> allocate -> execute -> verify."""
    PHASES = ("perception", "context", "planning", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, max_steps=8, max_agents=2):
        self.verifier = verifier
        self.planner = planner or Planner(max_steps=max_steps)
        self.coordinator = AgentCoordinator(router, verifier, max_agents=max_agents)

    def run(self, task: TaskSpec):
        task_check = self.verifier.verify_task(task)
        if not task_check.valid:
            return {"status": "rejected", "phase": "perception", "verification": task_check}

        state = CognitiveState("context", task.task_id, context=task.input)
        plan = self.planner.build(task)
        plan_check = self.planner.verify(plan, task)
        if not plan_check.valid:
            return {"status": "rejected", "phase": "planning", "verification": plan_check}

        results = self.coordinator.execute(task, plan)
        consensus = self.coordinator.verify_consensus(results)
        if not consensus.valid:
            return {"status": "rejected", "phase": "verification", "verification": consensus, "results": results}

        final_output = results[-1].output
        output_check = self.verifier.verify_output(final_output, stage="hypersynth_result")
        if not output_check.valid:
            return {"status": "rejected", "phase": "verification", "verification": output_check}

        final_state = CognitiveState("metacognition", task.task_id, context=task.input, confidence=1.0)
        return {
            "status": "completed",
            "phase": final_state.phase,
            "state": final_state,
            "plan": plan,
            "results": results,
            "verification": output_check,
        }
