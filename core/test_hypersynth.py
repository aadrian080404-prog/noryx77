import unittest

from .actions import ActionGate
from .agents import DeterministicAgent
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine


class HypersynthTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        self.memory = MemoryStore()
        self.kernel = Hypersynth(self.verifier, self.router, action_gate=gate, memory=self.memory)

    def task(self, **kwargs):
        values = dict(task_id="t1", task_type="research", objective="analyze", input="data", risk_class="normal")
        values.update(kwargs)
        return TaskSpec(**values)

    def test_full_controlled_cycle(self):
        result = self.kernel.run(self.task())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["phase"], "metacognition")
        self.assertTrue(result["verification"].valid)
        self.assertEqual(result["reflection"]["steps_executed"], 1)
        self.assertEqual(result["context"].version, 1)
        self.assertIsNotNone(self.memory.get("task:t1"))

    def test_invalid_task_is_rejected_before_planning(self):
        result = self.kernel.run(self.task(objective=""))
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["verification"].valid)
        self.assertEqual(result["phase"], "perception")

    def test_runtime_contains_audit(self):
        result = HypersynthRuntime(self.verifier, self.router).run(self.task())
        self.assertIn("audit", result)
        self.assertEqual(result["status"], "completed")

    def test_disagreement_is_fail_closed(self):
        from .coordination import AgentCoordinator
        coordinator = AgentCoordinator(self.router, self.verifier)
        results = (
            AgentResult("a", "t", "completed", "one", VerificationResult(True, "result")),
            AgentResult("b", "t", "completed", "two", VerificationResult(True, "result")),
        )
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

    def test_high_risk_action_is_denied(self):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "financial", risk_class="normal"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy")

    def test_unsupported_risk_is_denied(self):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "compute", risk_class="critical"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "security")

    def test_empty_router_fails_closed(self):
        empty = ResourceRouter()
        kernel = Hypersynth(self.verifier, empty)
        result = kernel.run(self.task(task_id="empty"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "allocation")

    def test_runtime_failure_is_controlled(self):
        class BrokenAgent:
            agent_id = "broken"
            def run(self, task):
                raise RuntimeError("boom")

        router = ResourceRouter()
        router.register(BrokenAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="broken"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "controlled_runtime_failure")


if __name__ == "__main__":
    unittest.main()
