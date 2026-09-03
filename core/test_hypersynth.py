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
            AgentResult("a", "t", "completed", "one", VerificationResult(True, "result")),
            AgentResult("b", "t", "completed", "two", VerificationResult(True, "result")),
        )
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

    def test_hypersynth_consensus_rejects_duplicate_agent_identity(self):
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", VerificationResult(True, "result")),
            AgentResult("a", "t2", "completed", "same", VerificationResult(True, "result")),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

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

    def test_agent_failure_is_rejected_at_execution_boundary(self):
        class BrokenAgent:
            agent_id = "broken"
            def run(self, task):
                raise RuntimeError("boom")

        router = ResourceRouter()
        router.register(BrokenAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="broken"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "execution")
        self.assertEqual(result["verification"].reason, "agent_execution_failure")

    def test_null_agent_output_is_rejected(self):
        class NullAgent:
            agent_id = "null"
            def run(self, task):
                return AgentResult(
                    self.agent_id, task.task_id, "completed", None,
                    VerificationResult(True, "result"),
                )

        router = ResourceRouter()
        router.register(NullAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="null"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "null_output")

    def test_simulation_identity_mismatch_is_fail_closed(self):
        class TamperingSimulator:
            def simulate(self, task, hypotheses):
                return tuple(
                    type("Simulation", (), {
                        "hypothesis_id": "forged",
                        "feasible": True,
                        "reason": "feasible",
                    })()
                    for _ in hypotheses
                )

            def verify(self, simulations):
                return VerificationResult(True, "simulation", "simulation_ok")

        kernel = Hypersynth(self.verifier, self.router, simulator=TamperingSimulator())
        result = kernel.run(self.task(task_id="sim-tamper"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "simulation_hypothesis_id_mismatch")

    def test_simulation_verifier_rejects_feasible_reason_mismatch(self):
        check = InternalSimulator().verify((
            SimulationResult("t1:h0", True, "fabricated"),
        ))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "feasible_reason_mismatch")

    def test_simulation_verifier_rejects_invalid_types_and_empty_fields(self):
        simulator = InternalSimulator()
        self.assertEqual(simulator.verify(("not-a-simulation",)).reason, "invalid_simulation_type")
        self.assertEqual(simulator.verify((SimulationResult("", True, "feasible"),)).reason, "invalid_hypothesis_id")
        self.assertEqual(simulator.verify((SimulationResult("t1:h0", True, ""),)).reason, "invalid_simulation_reason")
        self.assertEqual(simulator.verify((SimulationResult("t1:h0", 1, "feasible"),)).reason, "invalid_feasibility_flag")

    def test_metacognition_engine_accepts_complete_verified_pipeline(self):
        task = self.task()
        plan = Plan("t1", (PlanStep("s1", "analyze", "compute", "normal"),))
        hypotheses = (Hypothesis("t1:h0", "t1", "analyze", ("s1",)),)
        simulations = (SimulationResult("t1:h0", True, "feasible"),)
        results = (AgentResult("agent-1", "s1", "completed", "ok", VerificationResult(True, "result")),)
        check, reflection = MetacognitionEngine().reflect(task, plan, hypotheses, simulations, results, VerificationResult(True, "hypersynth_result"))
        self.assertTrue(check.valid)
        self.assertEqual(check.reason, "reflection_ok")
        self.assertEqual(reflection.agents_used, ("agent-1",))

    def test_metacognition_engine_rejects_pipeline_count_mismatch(self):
        task = self.task()
        plan = Plan("t1", (PlanStep("s1", "analyze", "compute", "normal"),))
        hypotheses = (Hypothesis("t1:h0", "t1", "analyze", ("s1",)),)
        check, reflection = MetacognitionEngine().reflect(task, plan, hypotheses, (), (), VerificationResult(True, "hypersynth_result"))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "pipeline_count_mismatch")
        self.assertIsNone(reflection)


if __name__ == "__main__":
    unittest.main()