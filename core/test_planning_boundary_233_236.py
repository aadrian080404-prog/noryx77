import unittest

from .contracts import TaskSpec
from .planning import Plan, PlanStep, Planner


class SpoofedPlan(Plan):
    @property
    def task_id(self):
        return "trusted-task"


class SpoofedStep(PlanStep):
    @property
    def risk_class(self):
        return "normal"


class SpoofedPlanningTask(TaskSpec):
    def __getattribute__(self, name):
        if name == "task_id":
            return "attacker-task"
        if name == "objective":
            return "attacker-objective"
        return super().__getattribute__(name)


class PlanningBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec("trusted-task", "analysis", "trusted objective", {})
        self.planner = Planner()

    def test_233_build_rejects_task_subclass(self):
        task = SpoofedPlanningTask("trusted-task", "analysis", "trusted objective", {})
        with self.assertRaises(TypeError):
            self.planner.build(task)

    def test_234_verify_rejects_task_subclass(self):
        task = SpoofedPlanningTask("trusted-task", "analysis", "trusted objective", {})
        plan = Plan("trusted-task", (PlanStep("trusted-task:0", "trusted objective"),))
        result = self.planner.verify(plan, task)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_task")

    def test_235_verify_rejects_plan_subclass(self):
        class MaliciousPlan(Plan):
            pass

        plan = MaliciousPlan("trusted-task", (PlanStep("trusted-task:0", "trusted objective"),))
        result = self.planner.verify(plan, self.task)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "invalid_plan_type")

    def test_236_verify_rejects_plan_step_subclass(self):
        class MaliciousStep(PlanStep):
            pass

        plan = Plan("trusted-task", (MaliciousStep("trusted-task:0", "trusted objective"),))
        result = self.planner.verify(plan, self.task)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "plan_step_type_invalid")

    def test_canonical_plan_remains_accepted(self):
        plan = self.planner.build(self.task)
        result = self.planner.verify(plan, self.task)
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "plan_ok")


if __name__ == "__main__":
    unittest.main()
