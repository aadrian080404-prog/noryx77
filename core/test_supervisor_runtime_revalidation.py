import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class SupervisorRuntimeRevalidationTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.agent = DeterministicAgent(self.verifier)
        self.agent.agent_id = "trusted"
        self.router.register(self.agent)
        self.supervisor = AgentSupervisor(self.router, self.verifier)
        self.task = TaskSpec("task-runtime", "research", "analyze", "input")

    def test_selected_agent_is_revalidated_before_execution(self):
        check = self.supervisor.validate_selected(self.task, self.agent)
        self.assertTrue(check.valid)
        self.assertEqual(check.reason, "agent_runtime_revalidated")

    def test_model_mutation_between_selection_and_execution_is_rejected(self):
        selected, decision = self.supervisor.select(self.task, preferred="trusted")
        self.assertTrue(decision.accepted)
        selected.model_class = "frontier"
        check = self.supervisor.validate_selected(self.task, selected)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_registration_runtime_failure")

    def test_capability_mutation_between_selection_and_execution_is_rejected(self):
        selected, decision = self.supervisor.select(self.task, preferred="trusted")
        self.assertTrue(decision.accepted)
        selected.capabilities = ("forged",)
        check = self.supervisor.validate_selected(self.task, selected)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_registration_runtime_failure")

    def test_replacement_object_between_selection_and_execution_is_rejected(self):
        replacement = DeterministicAgent(self.verifier)
        replacement.agent_id = "trusted"
        check = self.supervisor.validate_selected(self.task, replacement)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_registration_mismatch")


if __name__ == "__main__":
    unittest.main()
