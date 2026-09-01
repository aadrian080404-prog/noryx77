import unittest

from .contracts import TaskSpec
from .decomposition import Subtask, TaskDecomposer
from .errors import ContractViolation


class Attack20Tests(unittest.TestCase):
    def test_malformed_task_is_rejected_before_decomposition(self):
        task = object()
        with self.assertRaisesRegex(ContractViolation, "well-formed TaskSpec"):
            TaskDecomposer().decompose(task)

    def test_malformed_task_fields_are_rejected(self):
        task = TaskSpec("", "general", "objective", None)
        with self.assertRaisesRegex(ContractViolation, "well-formed TaskSpec"):
            TaskDecomposer().decompose(task)

    def test_decomposition_preserves_parent_identity(self):
        task = TaskSpec("task-20", "general", "perform objective", None)
        subtasks = TaskDecomposer().decompose(task)
        self.assertEqual(subtasks, (Subtask("task-20:0", "perform objective", "general"),))
        self.assertTrue(subtasks[0].subtask_id.startswith(task.task_id + ":"))
        self.assertEqual(subtasks[0].objective, task.objective)
        self.assertEqual(subtasks[0].task_type, task.task_type)

    def test_decomposer_returns_bounded_tuple(self):
        task = TaskSpec("task-20", "general", "perform objective", None)
        subtasks = TaskDecomposer().decompose(task)
        self.assertIsInstance(subtasks, tuple)
        self.assertEqual(len(subtasks), 1)


if __name__ == "__main__":
    unittest.main()
