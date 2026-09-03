import unittest

from .agents import DeterministicAgent
from .audit import AuditLog
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .supervisor import AgentSupervisor
from .tools import ToolExecutor
from .verification import VerificationEngine

class FoundationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()

    def test_unknown_tool_is_fail_closed(self):
        executor = ToolExecutor(self.policy, self.verifier)
        output, check = executor.execute(ActionSpec("a1", "UNKNOWN"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)

    def test_allowed_tool_output_is_verified(self):
        executor = ToolExecutor(self.policy, self.verifier)
        executor.capabilities.register("search", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a2", "search", target="ok"))
        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)

    def test_duplicate_tool_registration_is_rejected(self):
        executor = ToolExecutor(self.policy, self.verifier)
        executor.capabilities.register("search", lambda target, params: target)
        with self.assertRaises(ValueError):
            executor.capabilities.register("search", lambda target, params: "replacement")
        output, check = executor.execute(ActionSpec("a2b", "search", target="original"))
        self.assertEqual(output, "original")
        self.assertTrue(check.valid)

    def test_tool_policy_boundary_is_required(self):
        class NoPolicy:
            pass

        executor = ToolExecutor(NoPolicy(), self.verifier)
        executor.capabilities.register("search", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a2c", "search", target="should-not-run"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "policy_evaluation_failure")

    def test_tool_policy_exception_fails_closed(self):
        class ExplodingPolicy:
            def allows(self, action):
                raise RuntimeError("policy failure")

        executor = ToolExecutor(ExplodingPolicy(), self.verifier)
        executor.capabilities.register("search", lambda target, params: target)
        output, check = executor.execute(ActionSpec("a2d", "search", target="should-not-run"))
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "policy_evaluation_failure")

    def test_security_blocks_high_risk_by_default(self):
        boundary = SecurityBoundary(self.policy, self.verifier)
        check = boundary.inspect(ActionSpec("a3", "publish", risk_class="high"))
        self.assertFalse(check.allowed)

    def test_security_rejects_invalid_verifier_result(self):
        class InvalidVerifier:
            def verify_output(self, output, stage=None):
                return object()

        boundary = SecurityBoundary(self.policy, InvalidVerifier())
        check = boundary.verify(ActionSpec("a3b", "search"), "ok")
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_security_verification")

    def test_security_rejects_wrong_verification_stage(self):
        class WrongStageVerifier:
            def verify_output(self, output, stage=None):
                return VerificationResult(True, "agent_result", "forged")

        boundary = SecurityBoundary(self.policy, WrongStageVerifier())
        check = boundary.verify(ActionSpec("a3c", "search"), "ok")
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_security_verification")

    def test_supervisor_rejects_wrong_task_result(self):
        router = ResourceRouter()
        router.register(DeterministicAgent(self.verifier))
        task = TaskSpec("t1", "demo", "do", "input")
        result = AgentResult("deterministic", "other", "completed", output="ok")
        supervisor = AgentSupervisor(router, self.verifier)
        check = supervisor.admit(task, result)
        self.assertFalse(check.valid)

    def test_audit_rejects_empty_event(self):
        audit = AuditLog()
        with self.assertRaises(ValueError):
            audit.record("   ")

    def test_audit_record_is_mutation_isolated(self):
        audit = AuditLog()
        payload = {"nested": ["original"]}
        returned = audit.record("test", payload=payload)
        payload["nested"].append("caller-change")
        returned["payload"]["nested"].append("return-change")
        snapshot = audit.snapshot()
        self.assertEqual(snapshot[0]["payload"]["nested"], ["original"])

    def test_audit_snapshot_is_mutation_isolated(self):
        audit = AuditLog()
        audit.record("test", payload={"nested": ["original"]})
        snapshot = audit.snapshot()
        snapshot[0]["payload"]["nested"].append("caller-change")
        self.assertEqual(audit.snapshot()[0]["payload"]["nested"], ["original"])

if __name__ == "__main__":
    unittest.main()
