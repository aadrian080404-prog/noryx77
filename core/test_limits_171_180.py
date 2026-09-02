import math
import unittest

from .limits import RuntimeLimits


class RuntimeLimits171To180Tests(unittest.TestCase):
    def test_attack171_nan_task_time_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeLimits(max_task_seconds=float("nan"))

    def test_attack172_positive_infinity_task_time_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeLimits(max_task_seconds=float("inf"))

    def test_attack173_negative_infinity_task_time_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeLimits(max_task_seconds=float("-inf"))

    def test_attack174_finite_task_time_limit_remains_valid(self):
        limits = RuntimeLimits(max_task_seconds=30.0)
        self.assertTrue(math.isfinite(limits.max_task_seconds))
        self.assertEqual(limits.max_task_seconds, 30.0)

    def test_attack175_zero_task_time_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeLimits(max_task_seconds=0)


if __name__ == "__main__":
    unittest.main()
