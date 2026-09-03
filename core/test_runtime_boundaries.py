import unittest

from .actions import ActionGate
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .router import ResourceRouter
from .runtime import NORYXRuntime
from .security import SecurityBoundary
from .verification import VerificationEngine


class RuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.runtime = NORYXRuntime()

    def test_normal_task_completes(self):
        task = TaskSpec("t1", "compute", "test objective", "input")
        result = self.runtime.run(task)
        self.assertEqual(result["status"], "completed")

    def test_invalid_task_fails_closed(self):
        task = TaskSpec("", "compute", "test objective", "input")
        self.assertEqual(self.runtime.run(task)["status"], "rejected")

    def test_non_task_fails_closed_before_field_access(self):
        result = self.runtime.run(None)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "invalid_task_spec")

    def test_agent_exception_fails_closed(self):
        class FailingAgent:
            agent_id = "failing"
            def run(self, task):
                raise RuntimeError("boom")

        router = ResourceRouter()
        router.register(FailingAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        task = TaskSpec("t-exec", "compute", "short", "ok")
        result = runtime.run(task, agent_id="failing")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "agent_execution_failure")
        self.assertEqual(result["verification"].reason, "agent_execution_failure")

    def test_legacy_runtime_rejects_non_contract_agent_result(self):
        class ForgingAgent:
            agent_id = "real-agent"
            def run(self, task):
                return type("FakeResult", (), {
                    "agent_id": self.agent_id,
                    "task_id": task.task_id,
                    "status": "completed",
                    "output": "ok",
                    "verification": VerificationResult(True, "agent_result", "ok"),
                })()

        router = ResourceRouter()
        router.register(ForgingAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        task = TaskSpec("legacy-contract-tamper", "compute", "short", "ok")
        result = runtime.run(task, agent_id="real-agent")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "malformed_agent_result")

    def test_legacy_runtime_rejects_forged_agent_identity(self):
        class ForgingAgent:
            agent_id = "real-agent"
            def run(self, task):
                return AgentResult("forged-agent", task.task_id, "completed", "ok", VerificationResult(True, "agent_result", "ok"))

        router = ResourceRouter()
        router.register(ForgingAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        task = TaskSpec("legacy-identity-tamper", "compute", "short", "ok")
        result = runtime.run(task, agent_id="real-agent")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "agent_identity_mismatch")
        self.assertEqual(result["verification"].reason, "agent_identity_mismatch")

    def test_legacy_runtime_rejects_forged_task_identity(self):
        class ForgingAgent:
            agent_id = "real-agent"
            def run(self, task):
                return AgentResult(self.agent_id, "forged-task", "completed", "ok", VerificationResult(True, "agent_result", "ok"))

        router = ResourceRouter()
        router.register(ForgingAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        task = TaskSpec("legacy-task-tamper", "compute", "short", "ok")
        result = runtime.run(task, agent_id="real-agent")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "task_identity_mismatch")
        self.assertEqual(result["verification"].reason, "task_identity_mismatch")

    def test_legacy_runtime_rejects_incomplete_result_status(self):
        class IncompleteAgent:
            agent_id = "incomplete"
            def run(self, task):
                return AgentResult(self.agent_id, task.task_id, "processing", "ok", VerificationResult(True, "agent_result", "ok"))

        router = ResourceRouter()
        router.register(IncompleteAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        result = runtime.run(TaskSpec("legacy-status-tamper", "compute", "short", "ok"), agent_id="incomplete")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "invalid_result_status")

    def test_legacy_runtime_rejects_wrong_verification_stage(self):
        class ForgingAgent:
            agent_id = "stage-forger"
            def run(self, task):
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "runtime_result", "forged"))

        router = ResourceRouter()
        router.register(ForgingAgent())
        runtime = NORYXRuntime()
        runtime.router = router
        result = runtime.run(TaskSpec("legacy-stage-tamper", "compute", "short", "ok"), agent_id="stage-forger")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "verification_stage_mismatch")

    def test_unknown_agent_fails_closed(self):
        task = TaskSpec("unknown-agent", "compute", "short", "ok")
        result = self.runtime.run(task, agent_id="does-not-exist")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "agent_unavailable")

    def test_input_limit_is_enforced(self):
        runtime = NORYXRuntime(RuntimeLimits(max_input_chars=3))
        task = TaskSpec("t2", "compute", "test", "abcd")
        self.assertEqual(runtime.run(task)["status"], "rejected")

    def test_high_risk_action_is_denied(self):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, VerificationEngine())
        gate = ActionGate(policy, security, RuntimeLimits())
        action = ActionSpec("a1", "publish", risk_class="high")
        self.assertFalse(gate.authorize(action).allowed)

    def test_hypersynth_objective_limit_is_enforced(self):
        runtime = HypersynthRuntime(limits=RuntimeLimits(max_input_chars=4))
        task = TaskSpec("t3", "compute", "too long", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "objective_limit_exceeded")

    def test_hypersynth_output_limit_is_enforced(self):
        class LargeOutputAgent:
            agent_id = "large"
            def run(self, task):
                output = "x" * 20
                return AgentResult(self.agent_id, task.task_id, "completed", output, VerificationResult(True, "agent_result", "ok"))

        router = ResourceRouter()
        router.register(LargeOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_chars=5))
        task = TaskSpec("t4", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_limit_exceeded")

    def test_hypersynth_structured_output_item_limit_is_enforced(self):
        class StructuredOutputAgent:
            agent_id = "structured"
            def run(self, task):
                output = tuple(range(5))
                return AgentResult(self.agent_id, task.task_id, "completed", output, VerificationResult(True, "agent_result", "ok"))

        router = ResourceRouter()
        router.register(StructuredOutputAgent())
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_output_items=3))
        task = TaskSpec("t5", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "output_item_limit_exceeded")

    def test_hypersynth_execution_deadline_is_propagated_into_kernel(self):
        class FakeClock:
            def __init__(self):
                self.now = 0.0
            def __call__(self):
                return self.now

        class AdvancingAgent:
            agent_id = "advancing"
            def __init__(self, clock):
                self.clock = clock
            def run(self, task):
                self.clock.now += 2.0
                return AgentResult(self.agent_id, task.task_id, "completed", "ok", VerificationResult(True, "agent_result", "ok"))

        clock = FakeClock()
        router = ResourceRouter()
        router.register(AdvancingAgent(clock))
        runtime = HypersynthRuntime(router=router, limits=RuntimeLimits(max_task_seconds=1.0), clock=clock)
        task = TaskSpec("t6", "compute", "short", "ok")
        result = runtime.run(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "task_time_limit_exceeded")
        self.assertEqual(result["phase"], "execution")

    def test_runtime_limits_reject_non_finite_deadlines(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                RuntimeLimits(max_task_seconds=value)

    def test_top_level_runtime_exposes_bounded_hypersynth_mode(self):
        task = TaskSpec("hs1", "compute", "test objective", "input")
        result = self.runtime.run_hypersynth(task)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["results"])
        self.assertTrue(result["results"][-1].verification.valid)
        self.assertIn("hypersynth_start", [event["event"] for event in result["audit"]])

    def test_top_level_hypersynth_mode_uses_runtime_limits(self):
        runtime = NORYXRuntime(RuntimeLimits(max_input_chars=3))
        task = TaskSpec("hs2", "compute", "objective", "abcd")
        result = runtime.run_hypersynth(task)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "input_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
