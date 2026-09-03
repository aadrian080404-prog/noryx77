import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .router import ResourceRouter


class RuntimeBoundaryTests(unittest.TestCase):
    def test_hypersynth_objective_limit_is_enforced(self):
        runtime = HypersynthRuntime(limits=RuntimeLimits(max_input_chars=4))
        task = TaskSpec("t3", "compute", "too long", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "objective_limit_exceeded")

    def test_hypersynth_output_limit_is_enforced(self):
        class LargeOutputAgent:
            agent_id = "large"
            def run(self, task):
                output = "x" * 20
                return AgentResult(self.agent_id, task.task_id, "completed", output, VerificationResult(True, "agent_result", "ok"), task.execution_id)

        router = ResourceRouter()
        router.register(LargeOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_chars=5))
        task = TaskSpec("t4", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_limit_exceeded")

    def test_hypersynth_structured_output_item_limit_is_enforced(self):
        class StructuredOutputAgent:
            agent_id = "structured"
            def run(self, task):
                output = tuple(range(5))
                return AgentResult(self.agent_id, task.task_id, "completed", output, VerificationResult(True, "agent_result", "ok"), task.execution_id)

        router = ResourceRouter()
        router.register(StructuredOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_items=3))
        task = TaskSpec("t5", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_item_limit_exceeded")

    def test_hypersynth_execution_deadline_is_propagated_into_kernel(self):
        class FakeClock:
            def __init__(self):
                self.now = 0.0
            def __call__(self):
                return self.now

        class AdvancingAgent:
            agent_id = "advancing"
            def __init__(self, clock):
                self.clock = clock
            def run(self, task):
                self.clock.now += 2.0
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "agent_result", "ok"), task.execution_id)

        clock = FakeClock()
        router = ResourceRouter()
        router.register(AdvancingAgent(clock))
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_task_seconds=1.0), clock=clock)
        result = runtime.run(TaskSpec("deadline", "compute", "short", "ok"))
        self.assertEqual(result["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
