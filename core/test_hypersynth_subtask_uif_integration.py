import unittest

from .actions import ActionGate
from .agents import Agent
from .contracts import AgentResult, TaskSpec
from .hypersynth import Hypersynth
from .memory import MemoryStore
from .planning import Planner
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .subtask_uif import SubtaskUIFRouter
from .universal_intelligence import UniversalIntelligenceFabric
from .verification import VerificationEngine
from .limits import RuntimeLimits


class RecordingAgent(Agent):
    def __init__(self, agent_id, verifier, seen):
        self.agent_id = agent_id
        self.verifier = verifier
        self.seen = seen

    def run(self, task):
        self.seen.append((task.task_id, task.objective, dict(task.constraints)))
        output = f"verified:{task.objective}"
        return AgentResult(
            self.agent_id,
            task.task_id,
            "completed",
            output,
            self.verifier.verify_output(output, stage="agent_result"),
            task.execution_id,
        )


class SubtaskPlanner(Planner):
    def __init__(self):
        super().__init__(max_steps=2)


class HypersynthSubtaskUIFIntegrationTests(unittest.TestCase):
    def test_each_subtask_receives_its_own_uif_route(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        seen = []
        router.register(RecordingAgent("agent-a", verifier, seen))
        router.register(RecordingAgent("agent-b", verifier, seen))
        policy = PolicyEngine()
        gate = ActionGate(policy, SecurityBoundary(policy, verifier), RuntimeLimits(max_actions_per_task=2))
        fabric = UniversalIntelligenceFabric()
        kernel = Hypersynth(
            verifier,
            router,
            planner=SubtaskPlanner(),
            action_gate=gate,
            memory=MemoryStore(),
            max_agents=2,
            universal_intelligence=fabric,
            subtask_uif_router=SubtaskUIFRouter(fabric),
        )
        task = TaskSpec(
            "compound-uif",
            "research",
            "complete a compound objective",
            "controlled input",
            constraints={
                "subtasks": (
                    {"objective": "analyze the financial economics evidence"},
                    {"objective": "implement the software engineering design"},
                )
            },
            verification_requirements=("agent_result",),
            risk_class="normal",
            execution_id="execution-compound-uif",
        )
        result = kernel.run(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([item[0] for item in seen], ["compound-uif:0", "compound-uif:1"])
        self.assertEqual(seen[0][2]["_noryx7_specialist_domain"], "finance_economics")
        self.assertEqual(seen[1][2]["_noryx7_specialist_domain"], "software_engineering")
        self.assertFalse(seen[0][2]["_noryx7_route_authority"])
        self.assertFalse(seen[1][2]["_noryx7_route_authority"])
        events = [event["event"] for event in result["audit"]]
        self.assertIn("subtask_uif_routes", events)
        self.assertIn("subtask_uif_aggregate", events)


if __name__ == "__main__":
    unittest.main()
