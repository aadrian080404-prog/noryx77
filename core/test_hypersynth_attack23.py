import math
import unittest

from .contracts import TaskSpec
from .hypersynth_runtime import HypersynthRuntime


class SequenceClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class IncrementingClock:
    def __init__(self):
        self.value = 10.0

    def __call__(self):
        current = self.value
        self.value += 0.001
        return current


class Attack23Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack23", "analysis", "perform objective", "input")

    def test_non_callable_clock_fails_closed(self):
        runtime = HypersynthRuntime(clock=object())
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "controlled_runtime_failure")

    def test_non_numeric_clock_value_fails_closed(self):
        runtime = HypersynthRuntime(clock=lambda: "not-a-time")
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "controlled_runtime_failure")

    def test_non_finite_clock_value_fails_closed(self):
        runtime = HypersynthRuntime(clock=lambda: math.inf)
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "controlled_runtime_failure")

    def test_clock_regression_fails_closed(self):
        runtime = HypersynthRuntime(clock=SequenceClock([10.0, 9.0]))
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["verification"].reason, "task_time_limit_exceeded")

    def test_valid_monotonic_clock_is_accepted(self):
        runtime = HypersynthRuntime(clock=IncrementingClock())
        outcome = runtime.run(self.task())
        self.assertEqual(outcome["status"], "completed")


if __name__ == "__main__":
    unittest.main()
