import unittest

from .contracts import TaskSpec
from .provider import request_from_task


class ProviderRequestIsolationAdversarialTests(unittest.TestCase):
    def test_provider_request_does_not_alias_task_input(self):
        task_input = {"nested": {"value": 1}, "items": ["original"]}
        task = TaskSpec("isolation-1", "analysis", "objective", task_input)
        request = request_from_task(task)
        request.input["nested"]["value"] = 999
        request.input["items"].append("attacker")
        self.assertEqual(task.input, {"nested": {"value": 1}, "items": ["original"]})

    def test_provider_request_does_not_alias_nested_constraints(self):
        constraints = {"limits": {"max_steps": 3}, "tags": ["trusted"]}
        task = TaskSpec("isolation-2", "analysis", "objective", "input", constraints=constraints)
        request = request_from_task(task)
        request.constraints["limits"]["max_steps"] = 999
        request.constraints["tags"].append("attacker")
        self.assertEqual(task.constraints, {"limits": {"max_steps": 3}, "tags": ["trusted"]})

    def test_non_copyable_task_input_fails_closed(self):
        class NonCopyable:
            def __deepcopy__(self, memo):
                raise RuntimeError("no-copy")
        task = TaskSpec("isolation-3", "analysis", "objective", NonCopyable())
        with self.assertRaises(TypeError) as context:
            request_from_task(task)
        self.assertEqual(str(context.exception), "task_input_not_isolatable")


if __name__ == "__main__":
    unittest.main()
