import unittest

from .contracts import TaskSpec
from .planning import Plan, PlanStep, Planner


class Attack19Tests(unittest.TestCase):
    def setUp(self):
        self.task = TaskSpec("t19", "analysis", "perform bounded analysis", {})
        self.planner = Planner(max_steps=2)

    def test_non_plan_output_fails_closed(self):
        check = self.planner.verify(object(), self.task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_plan_type")

    def test_foreign_step_identity_is_rejected(self):
        plan = Plan(self.task.task_id, (PlanStep("foreign:0", self.task.objective),))
        check = self.planner.verify(plan, self.task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_step_parent_mismatch")

    def test_duplicate_step_identity_is_rejected(self):
        step = PlanStep("t19:0", "first")
        plan = Plan(self.task.task_id, (step, step))
        check = self.planner.verify(plan, self.task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_step_id_invalid")

    def test_risk_downgrade_is_rejected(self):
        task = TaskSpec("t19-high", "analysis", "perform high risk analysis", {}, risk_class="high")
        plan = Plan(task.task_id, (PlanStep("t19-high:0", task.objective, risk_class="normal"),))
        check = self.planner.verify(plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_step_risk_mismatch")

    def test_risk_upgrade_is_rejected(self):
        task = TaskSpec("t19-normal", "analysis", "perform normal analysis", {}, risk_class="normal")
        plan = Plan(task.task_id, (PlanStep("t19-normal:0", task.objective, risk_class="high"),))
        check = self.planner.verify(plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_step_risk_mismatch")

    def test_malformed_action_and_risk_types_fail_closed(self):
        action_plan = Plan(self.task.task_id, (PlanStep("t19:0", self.task.objective, action_type=[]),))
        risk_plan = Plan(self.task.task_id, (PlanStep("t19:0", self.task.objective, risk_class=[]),))
        self.assertEqual(self.planner.verify(action_plan, self.task).reason, "plan_step_action_invalid")
        self.assertEqual(self.planner.verify(risk_plan, self.task).reason, "plan_step_risk_invalid")

    def test_step_count_is_bounded(self):
        plan = Plan(
            self.task.task_id,
            (
                PlanStep("t19:0", "first"),
                PlanStep("t19:1", "second"),
                PlanStep("t19:2", "third"),
            ),
        )
        check = self.planner.verify(plan, self.task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "plan_bounds_invalid")

    def test_valid_plan_remains_accepted(self):
        plan = self.planner.build(self.task)
        check = self.planner.verify(plan, self.task)
        self.assertTrue(check.valid)
        self.assertEqual(check.stage, "plan")
        self.assertEqual(check.reason, "plan_ok")


if __name__ == "__main__":
    unittest.main()
