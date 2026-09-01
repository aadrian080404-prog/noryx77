import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .reasoning import CrossChecker, Hypothesis
from .router import ResourceRouter
from .agents import DeterministicAgent
from .verification import VerificationEngine


class ExplodingContext:
    def build(self, *args, **kwargs):
        raise RuntimeError("injected context failure")


class ExplodingRouter:
    def available(self):
        raise RuntimeError("injected router failure")


class DuplicateRouter(ResourceRouter):
    def available(self):
        return ("agent-a", "agent-a")


class Attack6Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack6", "research", "objective", "input", risk_class="normal")

    def test_context_exception_fails_closed(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        kernel = Hypersynth(verifier, router, context_manager=ExplodingContext())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "context")
        self.assertEqual(result["verification"].reason, "context_build_failure")

    def test_router_exception_fails_closed_before_execution(self):
        verifier = VerificationEngine()
        kernel = Hypersynth(verifier, ExplodingRouter())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "allocation")
        self.assertEqual(result["verification"].reason, "agent_discovery_failure")

    def test_duplicate_router_identity_fails_closed(self):
        verifier = VerificationEngine()
        kernel = Hypersynth(verifier, DuplicateRouter())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "duplicate_agent_identity")

    def test_invalid_router_identity_fails_closed(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        class InvalidRouter(ResourceRouter):
            def available(self):
                return ("",)
        kernel = Hypersynth(verifier, InvalidRouter())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "invalid_agent_identity")

    def test_cross_checker_rejects_hypothesis_parent_mismatch_independently(self):
        task = self.task()
        result = AgentResult("agent-a", "attack6:0", "completed", "ok", VerificationResult(True, "result", "ok"))
        forged = Hypothesis("attack6:h0", "other-task", "objective", ("attack6:0",))
        check = CrossChecker().verify(task, (result,), (forged,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "hypothesis_task_mismatch")


if __name__ == "__main__":
    unittest.main()
