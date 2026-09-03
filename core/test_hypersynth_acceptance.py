import unittest

from .actions import ActionGate
from .agents import Agent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .memory import MemoryStore
from .planning import Plan, PlanStep
from .policy import PolicyEngine
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine


class TwoStepPlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective), PlanStep(task.task_id + ":1", task.objective)))

    def verify(self, plan, task):
        if plan.task_id != task.task_id or len(plan.steps) != 2:
            return VerificationResult(False, "plan", "invalid_acceptance_plan")
        return VerificationResult(True, "plan", "plan_ok")


class ThreeStepPlanner:
    def build(self, task):
        return Plan(task.task_id, tuple(PlanStep(f"{task.task_id}:{i}", task.objective) for i in range(3)))

    def verify(self, plan, task):
        return VerificationResult(plan.task_id == task.task_id and len(plan.steps) == 3, "plan", "plan_ok")


class EchoAgent(Agent):
    def __init__(self, agent_id, verifier):
        self.agent_id = agent_id
        self.verifier = verifier

    def run(self, task):
        output = task.objective
        return AgentResult(self.agent_id, task.task_id, "completed", output, self.verifier.verify_output(output, stage="agent_result"), task.execution_id)


class NullAgent(Agent):
    agent_id = "null"

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id, "completed", None, None, task.execution_id)


class HypersynthAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()

    def task(self, **changes):
        values = {"task_id": "acceptance", "task_type": "research", "objective": "produce a verified result", "input": "controlled input", "risk_class": "normal"}
        values.update(changes)
        return TaskSpec(**values)

    def gate(self, max_actions=4):
        policy = PolicyEngine()
        security = SecurityBoundary(policy, self.verifier)
        return ActionGate(policy, security, RuntimeLimits(max_actions_per_task=max_actions))

    def test_hypersynth_multistep_two_agent_cycle(self):
        router = ResourceRouter()
        router.register(EchoAgent("agent-a", self.verifier))
        router.register(EchoAgent("agent-b", self.verifier))
        kernel = Hypersynth(self.verifier, router, planner=TwoStepPlanner(), action_gate=self.gate(), memory=MemoryStore(), max_agents=2)
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["phase"], "metacognition")
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["reflection"]["agents_used"], ("agent-a", "agent-b"))
        self.assertTrue(result["verification"].valid)

    def test_action_budget_is_fail_closed(self):
        router = ResourceRouter()
        router.register(EchoAgent("agent-a", self.verifier))
        router.register(EchoAgent("agent-b", self.verifier))
        kernel = Hypersynth(self.verifier, router, planner=TwoStepPlanner(), action_gate=self.gate(max_actions=1), max_agents=2)
        result = kernel.run(self.task(task_id="budget"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "execution")
        self.assertEqual(result["verification"].reason, "budget")

    def test_missing_agent_verification_is_rejected(self):
        router = ResourceRouter()
        router.register(NullAgent())
        kernel = Hypersynth(self.verifier, router, action_gate=self.gate())
        result = kernel.run(self.task(task_id="missing-verification"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "null_output")

    def test_runtime_unexpected_failure_is_fail_closed(self):
        class ExplodingVerifier(VerificationEngine):
            def verify_task(self, task):
                raise RuntimeError("verification infrastructure failure")
        runtime = HypersynthRuntime(verifier=ExplodingVerifier())
        result = runtime.run(self.task(task_id="runtime-failure"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "execution")
        self.assertEqual(result["reason"], "controlled_runtime_failure")
        self.assertIn("hypersynth_failure", [event["event"] for event in result["audit"]])

    def test_router_default_is_unambiguous(self):
        router = ResourceRouter()
        with self.assertRaises(LookupError):
            router.default_id()
        router.register(EchoAgent("only", self.verifier))
        self.assertEqual(router.default_id(), "only")

    def test_constructor_rejects_invalid_bounds(self):
        router = ResourceRouter()
        with self.assertRaises(ValueError):
            Hypersynth(self.verifier, router, max_steps=0)
        with self.assertRaises(ValueError):
            Hypersynth(self.verifier, router, max_agents=0)

    def test_plan_cannot_escape_agent_execution_bound(self):
        router = ResourceRouter()
        router.register(EchoAgent("only", self.verifier))
        kernel = Hypersynth(self.verifier, router, planner=ThreeStepPlanner(), action_gate=self.gate(), max_agents=2)
        result = kernel.run(self.task(task_id="plan-bound"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")
        self.assertEqual(result["verification"].reason, "plan_exceeds_execution_bound")

    def test_runtime_deadline_is_fail_closed(self):
        ticks = iter((0.0, 2.0))
        runtime = HypersynthRuntime(limits=RuntimeLimits(max_task_seconds=1.0), clock=lambda: next(ticks))
        result = runtime.run(self.task(task_id="deadline"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "task_time_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
