import unittest
from dataclasses import replace

from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .coordination import AgentCoordinator
from .identity import AgentIdentityAuthority, IdentityRegistry
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .supervisor import AgentSupervisor
from .verification import VerificationEngine


class IdentityBoundAgent(Agent):
    def __init__(self, agent_id, identity, verifier):
        self.agent_id = agent_id
        self.identity = identity
        self.verifier = verifier

    def run(self, task):
        check = self.verifier.verify_output("ok", stage="agent_result")
        return AgentResult(self.agent_id, task.task_id, "completed", "ok", check, task.execution_id)


class IdentityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.identity, self.private_key = AgentIdentityAuthority.generate("agent-a")
        self.registry = IdentityRegistry()
        self.registry.register(self.identity)
        self.agent = IdentityBoundAgent("agent-a", self.identity, self.verifier)
        self.task = TaskSpec("t", "research", "analyze", "data")
        self.plan = Plan("t", (PlanStep("s1", "analyze", "compute", "normal"),))

    def test_router_requires_trusted_identity_when_registry_enabled(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        self.assertIs(router.route("agent-a"), self.agent)

    def test_router_rejects_identity_substitution(self):
        attacker, _ = AgentIdentityAuthority.generate("attacker")
        forged = IdentityBoundAgent("agent-a", replace(self.identity, public_key=attacker.public_key), self.verifier)
        router = ResourceRouter(self.registry)
        with self.assertRaisesRegex(ValueError, "agent_identity_untrusted"):
            router.register(forged)

    def test_router_revocation_blocks_route(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        self.registry.revoke("agent-a")
        with self.assertRaisesRegex(LookupError, "agent_identity_untrusted"):
            router.route("agent-a")

    def test_supervisor_rejects_untrusted_selected_identity(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        supervisor = AgentSupervisor(router, self.verifier)
        self.registry.revoke("agent-a")
        selected, decision = supervisor.select(self.task, "agent-a")
        self.assertIsNone(selected)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "agent_identity_untrusted")

    def test_supervisor_admit_rejects_result_from_unknown_agent(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        supervisor = AgentSupervisor(router, self.verifier)
        result = AgentResult("unknown", self.task.task_id, "completed", "ok", VerificationResult(True, "agent_result"))
        check = supervisor.admit(self.task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "agent_unavailable")

    def test_supervisor_rejects_cross_execution_result_transplant(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        supervisor = AgentSupervisor(router, self.verifier)
        old_task = replace(self.task, execution_id="execution-old")
        new_task = replace(self.task, execution_id="execution-new")
        result = AgentResult("agent-a", "t", "completed", "ok", VerificationResult(True, "agent_result"), "execution-old")
        check = supervisor.admit(new_task, result)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "execution_identity_mismatch")
        self.assertTrue(supervisor.admit(old_task, result).valid)

    def test_coordinator_rejects_revoked_agent_before_execution(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        coordinator = AgentCoordinator(router, self.verifier)
        self.registry.revoke("agent-a")
        with self.assertRaisesRegex(RuntimeError, "agent_identity_untrusted:agent-a"):
            coordinator.execute(self.task, self.plan)

    def test_coordinator_accepts_trusted_identity(self):
        router = ResourceRouter(self.registry)
        router.register(self.agent)
        coordinator = AgentCoordinator(router, self.verifier)
        results = coordinator.execute(self.task, self.plan)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, "agent-a")
        self.assertTrue(results[0].execution_id)


if __name__ == "__main__":
    unittest.main()
