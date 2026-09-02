import unittest

from .contracts import TaskSpec
from .verification import VerificationEngine


class SpoofedTask(TaskSpec):
    def __getattribute__(self, name):
        if name == "task_id":
            return "attacker-task"
        if name == "task_type":
            return "dangerous"
        if name == "risk_class":
            return "normal"
        if name == "verification_requirements":
            return ("string",)
        return super().__getattribute__(name)


class VerificationBoundaryAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.task = TaskSpec("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))

    def test_attack_267_verify_task_rejects_task_subclass(self):
        spoofed = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        result = self.verifier.verify_task(spoofed)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_task_spec")

    def test_attack_268_continuity_rejects_subclass_parent(self):
        spoofed_parent = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        child = TaskSpec("trusted-task:child", "analysis", "trusted objective", {}, verification_requirements=("string",))
        result = self.verifier.verify_task_continuity(spoofed_parent, child)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_parent_task")

    def test_attack_269_continuity_rejects_subclass_child(self):
        parent = self.task
        spoofed_child = SpoofedTask("trusted-task:child", "analysis", "trusted objective", {}, verification_requirements=("string",))
        result = self.verifier.verify_task_continuity(parent, spoofed_child)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_child_task")

    def test_attack_270_canonical_task_remains_accepted(self):
        result = self.verifier.verify_task(self.task)
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "task_ok")

    def test_attack_271_pipeline_rejects_spoofed_task_before_output_acceptance(self):
        spoofed = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        results = self.verifier.verify_pipeline(spoofed, "trusted-output")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].valid)
        self.assertEqual(results[0].reason, "invalid_task_spec")


if __name__ == "__main__":
    unittest.main()
