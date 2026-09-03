import unittest

from .contracts import TaskSpec, VerificationResult
from .hypersynth_runtime import HypersynthRuntime


class ForgedVerifier:
    def verify_task(self, task):
        return object()


class RuntimeResultContractTests(unittest.TestCase):
    def test_runtime_rejects_forged_task_verification(self):
        runtime = HypersynthRuntime(verifier=ForgedVerifier())

        result = runtime.run(TaskSpec("t1", "search", "objective", "input"))

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "invalid_task_verification")

    def test_runtime_rejects_malformed_completed_kernel_result(self):
        runtime = HypersynthRuntime()
        runtime.kernel.run = lambda task, deadline_check=None: {"status": "completed", "results": ()}

        result = runtime.run(TaskSpec("t2", "search", "objective", "input"))

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "invalid_kernel_verification")

    def test_runtime_rejects_non_mapping_kernel_result(self):
        runtime = HypersynthRuntime()
        runtime.kernel.run = lambda task, deadline_check=None: object()

        result = runtime.run(TaskSpec("t3", "search", "objective", "input"))

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "execution")
        self.assertEqual(result["verification"].reason, "malformed_kernel_result")


if __name__ == "__main__":
    unittest.main()
