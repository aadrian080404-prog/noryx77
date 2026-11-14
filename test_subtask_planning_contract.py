import unittest

from .contracts import TaskSpec
from .decomposition import TaskDecomposer
from .planning import Planner


class SubtaskPlanningContractTests(unittest.TestCase):
    def task(self, constraints=None):
        return TaskSpec(
            "compound",
            "research",
            "Execute the compound research objective.",
            "source data",
            constraints=constraints or {},
            risk_class="normal",
        )

    def test_structured_subtasks_are_deterministic_and_bounded(self):
        task = self.task({"subtasks": [
            {"objective": "Collect the scientific evidence."},
            {"objective": "Compare the evidence.", "dependencies": ("0",)},
        ]})
        subtasks = TaskDecomposer(max_subtasks=4).decompose(task)
        self.assertEqual(tuple(item.subtask_id for item in subtasks), ("compound:0", "compound:1"))
        self.assertEqual(subtasks[1].dependencies, ("compound:0",))

    def test_planner_materializes_same_subtasks_in_deterministic_order(self):
        task = self.task({"subtasks": [
            {"objective": "Collect the scientific evidence."},
            {"objective": "Compare the evidence.", "dependencies": ("0",)},
        ]})
        plan = Planner(max_steps=4).build(task)
        self.assertEqual(tuple(step.step_id for step in plan.steps), ("compound:0", "compound:1"))
        self.assertEqual(plan.steps[1].dependencies, ("compound:0",))
        self.assertEqual(Planner(max_steps=4).verify(plan, task).reason, "plan_ok")

    def test_unknown_dependency_fails_closed(self):
        task = self.task({"subtasks": [
            {"objective": "Collect the scientific evidence."},
            {"objective": "Compare the evidence.", "dependencies": ("9",)},
        ]})
        with self.assertRaisesRegex(Exception, "subtask_dependency_unknown"):
            TaskDecomposer(max_subtasks=4).decompose(task)

    def test_forward_dependency_fails_closed(self):
        task = self.task({"subtasks": [
            {"objective": "Collect the scientific evidence.", "dependencies": ("1",)},
            {"objective": "Compare the evidence."},
        ]})
        with self.assertRaisesRegex(Exception, "subtask_dependency_order_invalid"):
            TaskDecomposer(max_subtasks=4).decompose(task)

    def test_planner_rejects_forward_dependency(self):
        task = self.task({"subtasks": [
            {"objective": "First step.", "dependencies": ("1",)},
            {"objective": "Second step."},
        ]})
        plan = Planner(max_steps=4).build(task)
        self.assertEqual(Planner(max_steps=4).verify(plan, task).reason, "plan_step_dependency_invalid")


if __name__ == "__main__":
    unittest.main()
