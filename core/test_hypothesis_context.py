import unittest

from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .reasoning import Hypothesis, HypothesisEngine
from .router import ResourceRouter
from .verification import VerificationEngine


class HypothesisContextBindingTests(unittest.TestCase):
    def task(self):
        return TaskSpec("hyp-context", "analysis", "answer", {})

    def plan(self):
        return Plan(
            "hyp-context",
            (PlanStep("hyp-context:0", "answer"),),
            context_version=3,
            context_source_ids=("hyp-context", "memory-1"),
        )

    def test_generation_preserves_exact_planning_context_binding(self):
        task = self.task()
        plan = self.plan()
        hypotheses = HypothesisEngine().generate(task, plan)
        self.assertEqual(len(hypotheses), 1)
        self.assertEqual(hypotheses[0].context_version, 3)
        self.assertEqual(hypotheses[0].context_source_ids, ("hyp-context", "memory-1"))
        self.assertTrue(HypothesisEngine().verify_against_plan(hypotheses, plan, task).valid)

    def test_context_version_tampering_is_rejected(self):
        task = self.task()
        plan = self.plan()
        forged = (Hypothesis("hyp-context:h0", task.task_id, "answer", ("hyp-context:0",), 4, plan.context_source_ids),)
        check = HypothesisEngine().verify_against_plan(forged, plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "hypothesis_context_mismatch")

    def test_context_sources_tampering_is_rejected(self):
        task = self.task()
        plan = self.plan()
        forged = (Hypothesis("hyp-context:h0", task.task_id, "answer", ("hyp-context:0",), plan.context_version, ("hyp-context", "foreign-memory")),)
        check = HypothesisEngine().verify_against_plan(forged, plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "hypothesis_context_mismatch")

    def test_plan_step_substitution_is_rejected(self):
        task = self.task()
        plan = self.plan()
        forged = (Hypothesis("hyp-context:h0", task.task_id, "answer", ("hyp-context:99",), plan.context_version, plan.context_source_ids),)
        check = HypothesisEngine().verify_against_plan(forged, plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "hypothesis_step_mismatch")

    def test_runtime_invokes_planning_hypothesis_binding_gate(self):
        class RejectingEngine(HypothesisEngine):
            def verify_against_plan(self, hypotheses, plan, task):
                return VerificationResult(False, "hypothesis", "runtime_binding_rejected")

        task = self.task()
        plan = self.plan()
        hypotheses = HypothesisEngine().generate(task, plan)
        kernel = Hypersynth.__new__(Hypersynth)
        kernel.hypothesis_engine = RejectingEngine()
        check = kernel._verify_hypothesis_integrity(hypotheses, plan, task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "runtime_binding_rejected")

    def test_full_runtime_rejects_forged_hypothesis_context(self):
        class ForgingEngine(HypothesisEngine):
            def generate(self, task, plan):
                hypotheses = super().generate(task, plan)
                hypothesis = hypotheses[0]
                forged = Hypothesis(
                    hypothesis.hypothesis_id,
                    hypothesis.task_id,
                    hypothesis.statement,
                    hypothesis.basis,
                    hypothesis.context_version + 1,
                    hypothesis.context_source_ids,
                )
                return (forged,)

        runtime = Hypersynth(VerificationEngine(), ResourceRouter(), hypothesis_engine=ForgingEngine())
        result = runtime.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")
        self.assertEqual(result["verification"].reason, "hypothesis_context_mismatch")


if __name__ == "__main__":
    unittest.main()
