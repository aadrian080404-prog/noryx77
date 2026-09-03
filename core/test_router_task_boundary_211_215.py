import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter


class SpoofedTask(TaskSpec):
    def __getattribute__(self, name):
        if name == "task_type":
            return "planning"
        if name == "constraints":
            return {"required_capabilities": ("forged",)}
        return super().__getattribute__(name)


class RouterTaskBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent())
        self.task = TaskSpec("routing-task", "analysis", "answer", {}, {"required_capabilities": ()})

    def test_attack_211_subclass_cannot_spoof_task_type_or_constraints(self):
        spoofed = SpoofedTask("routing-task", "analysis", "answer", {}, {"required_capabilities": ()})
        with self.assertRaisesRegex(ValueError, "invalid_task_contract"):
            self.router.route_for_task(spoofed)

    def test_attack_212_invalid_task_object_is_rejected_before_attribute_access(self):
        with self.assertRaisesRegex(ValueError, "invalid_task_contract"):
            self.router.route_for_task(object())

    def test_attack_213_malformed_task_is_rejected(self):
        malformed = TaskSpec("", "analysis", "answer", {})
        with self.assertRaisesRegex(ValueError, "invalid_task_contract"):
            self.router.route_for_task(malformed)

    def test_attack_214_canonical_task_routes_normally(self):
        selected = self.router.route_for_task(self.task)
        self.assertEqual(selected.agent_id, "deterministic")

    def test_attack_215_route_does_not_read_hostile_task_attributes(self):
        class Hostile:
            def __getattribute__(self, _name):
                raise AssertionError("hostile task attribute accessed")

        with self.assertRaisesRegex(ValueError, "invalid_task_contract"):
            self.router.route_for_task(Hostile())


if __name__ == "__main__":
    unittest.main()
