import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .reasoning import CrossChecker, Hypothesis, InternalSimulator, SimulationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .agents import DeterministicAgent
from .verification import VerificationEngine


class ForgedStatementHypothesisEngine:
    def generate(self, task, plan):
        return (Hypothesis(task.task_id + ":h0", task.task_id, "ATTACKER-CONTROLLED", (plan.steps[0].step_id,)),)

    def verify(self, hypotheses, task):
        return VerificationResult(True, "hypothesis", "forged_ok")


class Attack3Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack3", "research", "objective", "input", risk_class="normal")

    def test_hypothesis_statement_cannot_diverge_from_plan_objective(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        kernel = Hypersynth(verifier, router, hypothesis_engine=ForgedStatementHypothesisEngine())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")
        self.assertEqual(result["verification"].reason, "hypothesis_statement_mismatch")

    def test_cross_checker_rejects_swapped_result_mapping(self):
        task = self.task()
        hypotheses = (
            Hypothesis("attack3:h0", task.task_id, "step zero", ("attack3:0",)),
            Hypothesis("attack3:h1", task.task_id, "step one", ("attack3:1",)),
        )
        results = (
            AgentResult("a0", "attack3:1", "completed", "step one", VerificationResult(True, "result")),
            AgentResult("a1", "attack3:0", "completed", "step zero", VerificationResult(True, "result")),
        )
        check = CrossChecker().verify(task, results, hypotheses)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "result_task_mapping_mismatch")

    def test_simulator_verifier_rejects_duplicate_hypothesis_identity(self):
        check = InternalSimulator().verify((
            SimulationResult("attack3:h0", True, "feasible"),
            SimulationResult("attack3:h0", True, "feasible"),
        ))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "duplicate_simulation_id")

    def test_simulator_verifier_rejects_false_feasibility(self):
        check = InternalSimulator().verify((
            SimulationResult("attack3:h0", False, "invalid_hypothesis"),
        ))
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "simulation_rejected")


if __name__ == "__main__":
    unittest.main()
