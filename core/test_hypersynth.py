import unittest

from .actions import ActionGate
from .agents import Agent, DeterministicAgent
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
        result = self.kernel.run(self.task(execution_id="exec-1"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["execution_id"], "exec-1")
        self.assertEqual(result["results"][0].execution_id, "exec-1")
        self.assertEqual(result["state"].execution_id, "exec-1")

    def test_missing_execution_id_gets_fresh_run_binding(self):
        task = self.task()
        first = self.kernel.run(task)
        second = self.kernel.run(task)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "completed")
        self.assertTrue(first["execution_id"])
        self.assertTrue(second["execution_id"])
        self.assertNotEqual(first["execution_id"], second["execution_id"])
        self.assertEqual(task.execution_id, "")
        self.assertEqual(first["results"][0].execution_id, first["execution_id"])
        self.assertEqual(second["results"][0].execution_id, second["execution_id"])

    def test_child_execution_id_is_propagated(self):
        seen = []
        class CapturingAgent(Agent):
            agent_id = "capture"
            def run(self, task):
                seen.append(task.execution_id)
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "agent_result"), task.execution_id)
        router = ResourceRouter()
        router.register(CapturingAgent())
        kernel = Hypersynth(self.verifier, router)
        result = kernel.run(self.task(execution_id="parent-exec"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(seen, ["parent-exec"])

    def test_consensus_rejects_cross_execution_results(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", verified, "exec-a"),
            AgentResult("b", "t1", "completed", "same", verified, "exec-b"),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "execution_identity_mismatch")

    def test_consensus_rejects_missing_execution_identity(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", verified, ""),
            AgentResult("b", "t1", "completed", "same", verified, "exec-b"),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "execution_identity_mismatch")

    def test_consensus_rejects_all_missing_execution_identity(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((
            AgentResult("a", "t1", "completed", "same", verified, ""),
            AgentResult("b", "t1", "completed", "same", verified, ""),
        ))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_execution_identity")

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
        results = (AgentResult("a", "t", "completed", "one", VerificationResult(True, "agent_result")), AgentResult("b", "t", "completed", "two", VerificationResult(True, "agent_result")))
        check = coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_disagreement")

    def test_hypersynth_consensus_rejects_duplicate_agent_identity(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((AgentResult("a", "t1", "completed", "same", verified, "e"), AgentResult("a", "t1", "completed", "same", verified, "e")))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "duplicate_agent_result")

    def test_hypersynth_consensus_rejects_task_identity_mismatch(self):
        verified = VerificationResult(True, "agent_result", "verified")
        result = self.kernel._verify_consensus((AgentResult("a", "t1", "completed", "same", verified, "e"), AgentResult("b", "t2", "completed", "same", verified, "e")))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "task_identity_mismatch")

    def test_hypersynth_consensus_rejects_wrong_verification_stage(self):
        result = self.kernel._verify_consensus((AgentResult("a", "t1", "completed", "same", VerificationResult(True, "runtime_result", "verified"), "e"), AgentResult("b", "t1", "completed", "same", VerificationResult(True, "agent_result", "verified"), "e")))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "verification_stage_mismatch")

    def test_hypersynth_consensus_rejects_unverified_result(self):
        result = self.kernel._verify_consensus((AgentResult("a", "t1", "completed", "same", None, "e"),))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unverified_result")

    def test_high_risk_action_is_denied(self):
        policy = PolicyEngine(); security = SecurityBoundary(policy, self.verifier); gate = ActionGate(policy, security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "financial", risk_class="normal"))
        self.assertFalse(decision.allowed); self.assertEqual(decision.verification.reason, "policy")

    def test_unsupported_risk_is_denied(self):
        policy = PolicyEngine(); security = SecurityBoundary(policy, self.verifier); gate = ActionGate(policy, security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "compute", risk_class="critical"))
        self.assertFalse(decision.allowed); self.assertEqual(decision.verification.reason, "security")

    def test_empty_router_fails_closed(self):
        result = Hypersynth(self.verifier, ResourceRouter()).run(self.task(task_id="empty"))
        self.assertEqual(result["status"], "rejected"); self.assertEqual(result["phase"], "allocation")

    def test_agent_failure_is_rejected_at_execution_boundary(self):
        class BrokenAgent:
            agent_id = "broken"
            def run(self, task): raise RuntimeError("boom")
        router = ResourceRouter(); router.register(BrokenAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="broken"))
        self.assertEqual(result["status"], "rejected"); self.assertEqual(result["phase"], "execution"); self.assertEqual(result["verification"].reason, "execution_failure")

    def test_null_agent_output_is_rejected(self):
        class NullAgent:
            agent_id = "null"
            def run(self, task): return AgentResult(self.agent_id, task.task_id, "completed", None, VerificationResult(True, "result"), task.execution_id)
        router = ResourceRouter(); router.register(NullAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="null"))
        self.assertEqual(result["status"], "rejected"); self.assertEqual(result["phase"], "verification"); self.assertEqual(result["verification"].reason, "null_output")

    def test_agent_result_cannot_forge_selected_agent_identity(self):
        class ForgingAgent:
            agent_id = "real-agent"
            def run(self, task): return AgentResult("forged-agent", task.task_id, "completed", "ok", VerificationResult(True, "result"), task.execution_id)
        router = ResourceRouter(); router.register(ForgingAgent())
        result = HypersynthRuntime(self.verifier, router).run(self.task(task_id="identity-tamper"))
        self.assertEqual(result["status"], "rejected"); self.assertEqual(result["phase"], "verification"); self.assertEqual(result["verification"].reason, "agent_identity_mismatch")

    def test_simulation_identity_mismatch_is_fail_closed(self):
        class TamperingSimulator:
            def simulate(self, task, hypotheses): return tuple(type("Simulation", (), {"hypothesis_id": "forged", "feasible": True, "reason": "feasible"})() for _ in hypotheses)
            def verify(self, simulations): return VerificationResult(True, "simulation", "simulation_ok")
        result = Hypersynth(self.verifier, self.router, simulator=TamperingSimulator()).run(self.task(task_id="sim-tamper"))
        self.assertEqual(result["status"], "rejected"); self.assertEqual(result["phase"], "simulation"); self.assertEqual(result["verification"].reason, "simulation_hypothesis_id_mismatch")

    def test_simulation_verifier_rejects_feasible_reason_mismatch(self):
        check = InternalSimulator().verify((SimulationResult("t1:h0", True, "fabricated"),))
        self.assertFalse(check.valid); self.assertEqual(check.reason, "feasible_reason_mismatch")

    def test_simulation_verifier_rejects_invalid_types_and_empty_fields(self):
        simulator = InternalSimulator()
        self.assertEqual(simulator.verify(("not-a-simulation",)).reason, "invalid_simulation_type")
        self.assertEqual(simulator.verify((SimulationResult("", True, "feasible"),)).reason, "invalid_hypothesis_id")
        self.assertEqual(simulator.verify((SimulationResult("t1:h0", True, ""),)).reason, "invalid_simulation_reason")
        self.assertEqual(simulator.verify((SimulationResult("t1:h0", 1, "feasible"),)).reason, "invalid_feasibility_flag")

    def test_metacognition_engine_accepts_complete_verified_pipeline(self):
        task = self.task(execution_id="e"); plan = Plan("t1", (PlanStep("s1", "analyze", "compute", "normal"),)); hypotheses = (Hypothesis("t1:h0", "t1", "analyze", ("s1",)),); simulations = (SimulationResult("t1:h0", True, "feasible"),); results = (AgentResult("agent-1", "s1", "completed", "ok", VerificationResult(True, "agent_result"), "e"),)
        check, reflection = MetacognitionEngine().reflect(task, plan, hypotheses, simulations, results, VerificationResult(True, "hypersynth_result"))
        self.assertTrue(check.valid); self.assertEqual(check.reason, "reflection_ok"); self.assertEqual(reflection.agents_used, ("agent-1",))


if __name__ == "__main__": unittest.main()
