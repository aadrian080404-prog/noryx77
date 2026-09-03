import unittest

from .contracts import TaskSpec, VerificationResult
from .decomposition import Subtask
from .hypersynth import Hypersynth
from .router import ResourceRouter
from .verification import VerificationEngine


class HypersynthDecompositionBoundaryTests(unittest.TestCase):
    def task(self):
        return TaskSpec("decomp", "research", "analyze", "data", risk_class="normal")

    def kernel(self, decomposer):
        return Hypersynth(VerificationEngine(), ResourceRouter(), decomposer=decomposer)

    def test_decomposer_must_return_tuple_of_subtasks(self):
        class ForgedDecomposer:
            def decompose(self, task):
                return [Subtask("decomp:0", "analyze", "research")]

        result = self.kernel(ForgedDecomposer()).run(self.task())
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "invalid_subtask_collection")

    def test_decomposer_cannot_inject_foreign_subtask_identity(self):
        class ForgedDecomposer:
            def decompose(self, task):
                return (Subtask("foreign:0", "analyze", "research"),)

        result = self.kernel(ForgedDecomposer()).run(self.task())
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "subtask_task_identity_mismatch")

    def test_decomposer_cannot_change_task_type(self):
        class ForgedDecomposer:
            def decompose(self, task):
                return (Subtask("decomp:0", "analyze", "finance"),)

        result = self.kernel(ForgedDecomposer()).run(self.task())
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "subtask_task_type_mismatch")

    def test_decomposer_cannot_duplicate_subtask_identity(self):
        class ForgedDecomposer:
            def decompose(self, task):
                item = Subtask("decomp:0", "analyze", "research")
                return (item, item)

        result = self.kernel(ForgedDecomposer()).run(self.task())
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "invalid_subtask_identity")

    def test_decomposer_cannot_return_wrong_subtask_type(self):
        class ForgedDecomposer:
            def decompose(self, task):
                return (object(),)

        result = self.kernel(ForgedDecomposer()).run(self.task())
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "invalid_subtask_type")


if __name__ == "__main__":
    unittest.main()
