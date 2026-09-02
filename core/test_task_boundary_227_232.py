import unittest

from .agents import DeterministicAgent, ProviderAgent
from .contracts import TaskSpec
from .provider import ProviderResponse, request_from_task
from .reasoning import CrossChecker, Hypothesis, InternalSimulator
from .verification import VerificationEngine


class SpoofedTask(TaskSpec):
    def __getattribute__(self, name):
        if name == "task_id":
            return "attacker-task"
        if name == "objective":
            return "attacker-objective"
        if name == "constraints":
            return {"max_steps": 999}
        return super().__getattribute__(name)


class TaskBoundaryProvider:
    provider_id = "trusted"
    model_id = "model-v1"

    def execute(self, _request):
        return ProviderResponse("ok", self.provider_id, self.model_id, {})


class TaskBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.real_task = TaskSpec("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        self.spoofed_task = SpoofedTask("trusted-task", "analysis", "trusted objective", {}, verification_requirements=("string",))
        self.verifier = VerificationEngine()

    def test_227_request_builder_rejects_task_subclass(self):
        with self.assertRaises(TypeError) as context:
            request_from_task(self.spoofed_task)
        self.assertEqual(str(context.exception), "task_must_be_well_formed")

    def test_228_deterministic_agent_rejects_task_subclass_before_verifier(self):
        result = DeterministicAgent(self.verifier).run(self.spoofed_task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.task_id, "__invalid_task__")
        self.assertEqual(result.verification.reason, "invalid_task_type")

    def test_229_provider_agent_rejects_task_subclass_before_provider(self):
        provider = TaskBoundaryProvider()
        result = ProviderAgent("agent", provider, self.verifier).run(self.spoofed_task)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.task_id, "__invalid_task__")
        self.assertEqual(result.verification.reason, "invalid_task_type")

    def test_230_hypothesis_generation_rejects_task_subclass(self):
        from .planning import Plan, PlanStep
        plan = Plan("trusted-task", (PlanStep("trusted-task:s1", "step"),))
        self.assertEqual(self._hypothesis_engine().generate(self.spoofed_task, plan), ())

    def test_231_simulator_rejects_task_subclass(self):
        hypothesis = Hypothesis("h1", "trusted-task", "step", ("trusted-task:s1",))
        self.assertEqual(InternalSimulator().simulate(self.spoofed_task, (hypothesis,)), ())

    def test_232_cross_checker_rejects_task_subclass(self):
        hypothesis = Hypothesis("h1", "trusted-task", "step", ("trusted-task:s1",))
        self.assertFalse(CrossChecker().verify(self.spoofed_task, (), (hypothesis,)).valid)

    @staticmethod
    def _hypothesis_engine():
        from .reasoning import HypothesisEngine
        return HypothesisEngine()

    def test_canonical_task_remains_accepted(self):
        result = ProviderAgent("agent", TaskBoundaryProvider(), self.verifier).run(self.real_task)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.output, "ok")


if __name__ == "__main__":
    unittest.main()
