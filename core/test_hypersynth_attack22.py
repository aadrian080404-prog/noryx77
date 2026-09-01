import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth_runtime import HypersynthRuntime
from .hypersynth import CognitiveState


class ForgedKernel:
    def __init__(self, result):
        self.result = result

    def run(self, task):
        return self.result


class Attack22Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack22", "analysis", "perform objective", "input")

    def valid_result(self, task_id="attack22:0", agent_id="deterministic"):
        verification = VerificationResult(True, "hypersynth_result", "ok")
        agent_verification = VerificationResult(True, "agent_result", "ok")
        return {
            "status": "completed",
            "phase": "metacognition",
            "state": CognitiveState("metacognition", "attack22"),
            "verification": verification,
            "results": (AgentResult(agent_id, task_id, "completed", "output", agent_verification),),
        }

    def runtime_with(self, result):
        runtime = HypersynthRuntime()
        runtime.kernel = ForgedKernel(result)
        return runtime

    def test_foreign_prefixed_result_task_id_is_rejected(self):
        result = self.valid_result(task_id="attack22:999")
        runtime = self.runtime_with(result)
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "kernel_result_task_identity_mismatch")

    def test_duplicate_result_task_identity_is_rejected(self):
        result = self.valid_result()
        result["results"] = (
            result["results"][0],
            AgentResult("second", "attack22:0", "completed", "output", VerificationResult(True, "agent_result", "ok")),
        )
        runtime = self.runtime_with(result)
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "kernel_result_count_mismatch")

    def test_exact_runtime_result_binding_is_accepted(self):
        result = self.valid_result()
        runtime = self.runtime_with(result)
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "completed")


if __name__ == "__main__":
    unittest.main()
