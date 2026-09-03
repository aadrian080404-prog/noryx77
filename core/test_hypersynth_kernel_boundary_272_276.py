import unittest

from .contracts import TaskSpec
from .hypersynth import Hypersynth
from .hypersynth_kernel import AttestedHypersynthKernel
from .router import ResourceRouter
from .verification import VerificationEngine


class SpoofedTask(TaskSpec):
    def __getattribute__(self, name):
        if name == "task_id":
            return "attacker-task"
        if name == "risk_class":
            return "normal"
        if name == "verification_requirements":
            return ("string",)
        return super().__getattribute__(name)


class CountingKernel(Hypersynth):
    def __init__(self):
        super().__init__(VerificationEngine(), ResourceRouter())
        self.calls = 0

    def run(self, task):
        self.calls += 1
        return {"status": "rejected", "phase": "test"}


class HypersynthKernelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.kernel = CountingKernel()
        self.attested = AttestedHypersynthKernel(self.kernel)
        self.task = TaskSpec("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))

    def test_attack_272_subclass_task_is_rejected_before_kernel_execution(self):
        spoofed = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        with self.assertRaises(RuntimeError) as raised:
            self.attested.run(spoofed)
        self.assertEqual(str(raised.exception), "malformed_hypersynth_task_contract")
        self.assertEqual(self.kernel.calls, 0)

    def test_attack_273_malformed_task_is_rejected_before_kernel_execution(self):
        malformed = TaskSpec("", "analysis", "trusted objective", {})
        with self.assertRaises(RuntimeError) as raised:
            self.attested.run(malformed)
        self.assertEqual(str(raised.exception), "malformed_hypersynth_task_contract")
        self.assertEqual(self.kernel.calls, 0)

    def test_attack_274_canonical_task_reaches_kernel(self):
        result = self.attested.run(self.task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.kernel.calls, 1)

    def test_attack_275_task_identity_is_read_from_canonical_object(self):
        result = self.attested.run(self.task)
        self.assertNotIn("attacker-task", repr(result))
        self.assertEqual(self.kernel.calls, 1)

    def test_attack_276_spoofed_task_cannot_change_attestation_inputs(self):
        spoofed = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        with self.assertRaises(RuntimeError):
            self.attested.run(spoofed)
        self.assertEqual(self.kernel.calls, 0)


if __name__ == "__main__":
    unittest.main()
