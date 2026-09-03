import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter


class RouterExecutionBindingTests(unittest.TestCase):
    def setUp(self):
        self.router = ResourceRouter()
        self.agent = DeterministicAgent()
        self.router.register(self.agent)
        self.task = TaskSpec("binding-task", "analysis", "answer", {}, {"required_capabilities": ()})

    def test_attack_216_stale_selected_agent_is_rejected_after_registration_mutation(self):
        selected = self.router.route_for_task(self.task)
        self.agent.model_class = "frontier"
        with self.assertRaisesRegex(RuntimeError, "registered_agent_metadata_mutated"):
            self.router.resolve_execution(selected)

    def test_attack_217_stale_selected_agent_run_swap_is_rejected(self):
        selected = self.router.route_for_task(self.task)
        original_run = self.agent.run
        self.agent.run = lambda _task: None
        with self.assertRaisesRegex(RuntimeError, "registered_agent_metadata_mutated"):
            self.router.resolve_execution(selected)
        self.agent.run = original_run

    def test_attack_218_stale_agent_identity_is_rejected(self):
        selected = self.router.route_for_task(self.task)
        selected.agent_id = "different"
        with self.assertRaisesRegex((LookupError, RuntimeError), "(agent_registration_mismatch|registered_agent_metadata_mutated)"):
            self.router.resolve_execution(selected)

    def test_attack_219_resolve_for_task_captures_selected_agent_and_exact_callable(self):
        selected, execute = self.router.resolve_for_task(self.task)
        self.assertIs(selected, self.agent)
        self.assertIs(execute.__self__, self.agent)
        self.assertIs(execute.__func__, DeterministicAgent.run)

    def test_attack_220_captured_callable_remains_the_original_execution_binding(self):
        selected, execute = self.router.resolve_for_task(self.task)
        selected.run = lambda _task: (_ for _ in ()).throw(AssertionError("swapped callable executed"))
        result = execute(self.task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.task_id, self.task.task_id)


if __name__ == "__main__":
    unittest.main()
