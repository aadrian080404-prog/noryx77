import unittest

from .actions import ActionGate
from .agents import DeterministicAgent
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .metacognition import MetacognitionEngine
from .planning import Plan, PlanStep
from .policy import PolicyEngine
from .reasoning import Hypothesis, InternalSimulator, SimulationResult
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
        self.assertTrue(result["reflection"].result_verified)
        self.assertEqual(result["reflection"].steps_executed, 1)
        self.assertEqual(result["reflection"].confidence, 1.0)
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
            AgentResult("a", "t", "completed", "one", VerificationResult(True, "agent_result", "verified")),
            AgentResult("b", "t", "completed", "two", VerificationResult(True, "agent_result", "verified")),
        )
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

    def test_hypersynth_consensus_rejects_duplicate_agent_identity(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", verified),
            AgentResult("a", "t1", "completed", "same", verified),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

    def test_hypersynth_consensus_rejects_task_identity_mismatch(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", verified),
            AgentResult("b", "t2", "completed", "same", verified),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "task_identity_mismatch")

    def test_hypersynth_consensus_rejects_wrong_verification_stage(self):
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", VerificationResult(True, "runtime_result", "verified")),
            AgentResult("b", "t1", "completed", "same", VerificationResult(True, "agent_result", "verified")),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "verification_stage_mismatch")

    def test_hypersynth_consensus_rejects_unverified_result(self):
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", None),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unverified_result")

    def test_high_risk_action_is_denied(self):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        gate = ActionGate(policy, security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "financial", risk_class="normal"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy")
