import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .hypersynth_runtime import HypersynthRuntime
from .planning import Plan, PlanStep
from .reasoning import Hypothesis
from .router import ResourceRouter
from .verification import VerificationEngine


class BasePlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "compute", task.risk_class),))

    def verify(self, plan, task):
        return VerificationResult(True, "plan", "forged_ok")


class ForgedRiskPlanner(BasePlanner):
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "compute", "high"),))


class ForgedHypothesisEngine:
    def generate(self, task, plan):
        return (Hypothesis(task.task_id + ":h0", "forged-parent", plan.steps[0].objective, (plan.steps[0].step_id,)),)

    def verify(self, hypotheses, task):
        return VerificationResult(True, "hypothesis", "forged_ok")


class MalformedDecomposer:
    def decompose(self, task):
        # Non-empty ID is insufficient: the child must preserve the parent's contract.
        from .decomposition import Subtask
        return (Subtask("attacker-child", "", ""),)


class Attack2Tests(unittest.TestCase):
    def task(self, **changes):
        values = dict(task_id="attack", task_type="research", objective="objective", input="input", risk_class="normal")
        values.update(changes)
        return TaskSpec(**values)

    def kernel(self, **kwargs):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return Hypersynth(verifier, router, **kwargs)

    def test_forged_planner_cannot_change_risk_class(self):
        result = self.kernel(planner=ForgedRiskPlanner()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")

    def test_forged_hypothesis_cannot_change_parent_task_identity(self):
        result = self.kernel(hypothesis_engine=ForgedHypothesisEngine()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")

    def test_malformed_decomposition_is_rejected_before_planning(self):
        result = self.kernel(decomposer=MalformedDecomposer()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "context")

    def test_runtime_contains_no_success_after_kernel_rejection(self):
        result = HypersynthRuntime(planner=ForgedRiskPlanner()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertNotEqual(result.get("phase"), "metacognition")


if __name__ == "__main__":
    unittest.main()
