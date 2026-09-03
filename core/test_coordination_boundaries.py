import unittest

from .agents import Agent, DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .coordination import AgentCoordinator
from .identity import AgentIdentityAuthority, IdentityRegistry
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine


class CoordinationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.coordinator = AgentCoordinator(self.router, self.verifier)
        self.task = TaskSpec("t", "research", "analyze", "data")
        self.plan = Plan("t", (PlanStep("s1", "analyze", "compute", "normal"),))

    def test_execute_accepts_agent_result_with_bound_verification_stage(self):
        results = self.coordinator.execute(self.task, self.plan)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].verification.stage, "agent_result")

    def test_execute_rejects_forged_agent_identity(self):
        class ForgingAgent(Agent):
            agent_id = "real"
            def run(self, task):
                return AgentResult("forged", task.task_id, "completed", "ok", VerificationResult(True, "agent_result"))

        router = ResourceRouter()
        router.register(ForgingAgent())
        coordinator = AgentCoordinator(router, self.verifier)
        with self.assertRaisesRegex(RuntimeError, "agent_result_identity_mismatch:real"):
            coordinator.execute(self.task, self.plan)

    def test_execute_rejects_wrong_verification_stage(self):
        class WrongStageAgent(Agent):
            agent_id = "wrong-stage"
            def run(self, task):
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "runtime_result"))

        router = ResourceRouter()
        router.register(WrongStageAgent())
        coordinator = AgentCoordinator(router, self.verifier)
        with self.assertRaisesRegex(RuntimeError, "agent_result_verification_stage_mismatch:wrong-stage"):
            coordinator.execute(self.task, self.plan)

    def test_consensus_rejects_wrong_verification_stage(self):
        result = AgentResult("agent", "s1", "completed", "ok", VerificationResult(True, "runtime_result", "forged"))
        check = self.coordinator.verify_consensus((result,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "verification_stage_mismatch")

    def test_consensus_rejects_duplicate_agent_identity(self):
        verified = VerificationResult(True, "agent_result", "verified")
        results = (
            AgentResult("same-agent", "s1", "completed", "ok", verified),
            AgentResult("same-agent", "s2", "completed", "ok", verified),
        )
        check = self.coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "duplicate_agent_identity")

    def test_consensus_rejects_unknown_agent_when_identity_registry_enabled(self):
        registry = IdentityRegistry()
        trusted, _ = AgentIdentityAuthority.generate("trusted")
        registry.register(trusted)
        router = ResourceRouter(registry)
        router.register(IdentityAgent("trusted", trusted, self.verifier))
        coordinator = AgentCoordinator(router, self.verifier)
        verified = VerificationResult(True, "agent_result", "verified")
        result = AgentResult("unknown", "t", "completed", "same", verified)
        check = coordinator.verify_consensus((result,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_unavailable")

    def test_consensus_rejects_revoked_agent(self):
        registry = IdentityRegistry()
        identity, _ = AgentIdentityAuthority.generate("trusted")
        registry.register(identity)
        router = ResourceRouter(registry)
        router.register(IdentityAgent("trusted", identity, self.verifier))
        coordinator = AgentCoordinator(router, self.verifier)
        verified = VerificationResult(True, "agent_result", "verified")
        result = AgentResult("trusted", "t", "completed", "same", verified)
        registry.revoke("trusted")
        check = coordinator.verify_consensus((result,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_identity_untrusted")

    def test_result_issued_before_revocation_is_rejected_after_revocation(self):
        registry = IdentityRegistry()
        identity, _ = AgentIdentityAuthority.generate("trusted")
        registry.register(identity)
        router = ResourceRouter(registry)
        router.register(IdentityAgent("trusted", identity, self.verifier))
        coordinator = AgentCoordinator(router, self.verifier)
        result = IdentityAgent("trusted", identity, self.verifier).run(TaskSpec("t", "research", "analyze", "data", execution_id="exec-1"))
        registry.revoke("trusted")
        check = coordinator.verify_consensus((result,))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_identity_untrusted")

    def test_consensus_rejects_same_task_id_from_different_executions(self):
        verified = VerificationResult(True, "agent_result", "verified")
        results = (
            AgentResult("agent-a", "t", "completed", "same", verified, "exec-a"),
            AgentResult("agent-b", "t", "completed", "same", verified, "exec-b"),
        )
        check = self.coordinator.verify_consensus(results)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "execution_identity_mismatch")

    def test_execute_rejects_revocation_during_agent_execution(self):
        registry = IdentityRegistry()
        identity, _ = AgentIdentityAuthority.generate("revoked-midflight")
        registry.register(identity)

        class RevokingAgent(IdentityAgent):
            def run(self, task):
                result = super().run(task)
                registry.revoke(self.agent_id)
                return result

        router = ResourceRouter(registry)
        router.register(RevokingAgent("revoked-midflight", identity, self.verifier))
        coordinator = AgentCoordinator(router, self.verifier)
        plan = Plan("t", (PlanStep("s1", "analyze", "compute", "normal"),))
        with self.assertRaisesRegex(RuntimeError, "agent_identity_untrusted:revoked-midflight"):
            coordinator.execute(self.task, plan)


class IdentityAgent(Agent):
    def __init__(self, agent_id, identity, verifier):
        self.agent_id = agent_id
        self.identity = identity
        self.verifier = verifier

    def run(self, task):
        check = self.verifier.verify_output("ok", stage="agent_result")
        return AgentResult(self.agent_id, task.task_id, "completed", "ok", check, task.execution_id)


if __name__ == "__main__":
    unittest.main()
