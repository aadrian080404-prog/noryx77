import unittest

from .contracts import TaskSpec
from .planning import Plan, PlanStep
from .reasoning import Hypothesis, HypothesisEngine


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


if __name__ == "__main__":
    unittest.main()
