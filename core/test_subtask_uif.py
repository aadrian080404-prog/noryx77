import unittest

from .contracts import TaskSpec
from .decomposition import Subtask
from .subtask_uif import SubtaskUIFRouter


class SubtaskUIFRoutingTests(unittest.TestCase):
    def task(self):
        return TaskSpec(
            "compound-uif",
            "research",
            "Execute a compound objective.",
            "Provide the supporting context.",
            constraints={},
            verification_requirements=("agent_result",),
            risk_class="normal",
            execution_id="execution-compound-uif",
        )

    def test_each_subtask_is_routed_from_its_own_objective(self):
        task = self.task()
        subtasks = (
            Subtask("compound-uif:0", "Implement the Python code and tests.", task.task_type),
            Subtask("compound-uif:1", "Analyze the financial market and revenue.", task.task_type),
        )
        result = SubtaskUIFRouter().route(task, subtasks)
        self.assertTrue(result.verification.valid)
        self.assertEqual(result.routes[0].route.domain, "software_engineering")
        self.assertEqual(result.routes[1].route.domain, "finance_economics")
        self.assertNotEqual(result.routes[0].route.domain, result.routes[1].route.domain)

    def test_route_constraints_are_subtask_specific_and_never_authority(self):
        task = self.task()
        subtask = Subtask("compound-uif:0", "Review the financial market revenue.", task.task_type)
        routed = SubtaskUIFRouter().route(task, (subtask,))
        constraints = SubtaskUIFRouter.constraints_for(task, routed.routes[0])
        self.assertEqual(constraints["_noryx7_subtask_id"], "compound-uif:0")
        self.assertEqual(constraints["_noryx7_specialist_domain"], "finance_economics")
        self.assertEqual(constraints["_noryx7_cognitive_budget"], "specialist")
        self.assertFalse(constraints["_noryx7_route_authority"])

    def test_invalid_subtask_identity_fails_closed(self):
        task = self.task()
        subtask = Subtask("foreign:0", "Review the financial market.", task.task_type)
        result = SubtaskUIFRouter().route(task, (subtask,))
        self.assertFalse(result.verification.valid)
        self.assertEqual(result.verification.reason, "subtask_identity_invalid")


if __name__ == "__main__":
    unittest.main()
