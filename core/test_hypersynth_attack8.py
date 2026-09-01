import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .reasoning import CrossChecker, Hypothesis, InternalSimulator, SimulationResult
from .router import ResourceRouter
from .verification import VerificationEngine


class ForgedPlanPlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "execute", "normal"),))

    def verify(self, plan, task):
        return VerificationResult(True, "planning", "forged_planner_ok")


class ForgedHypothesisEngine:
    def generate(self, task, plan):
        return (Hypothesis(task.task_id + ":h0", task.task_id, "forged objective", (plan.steps[0].step_id,)),)

    def verify(self, hypotheses, task):
        return VerificationResult(True, "hypothesis", "forged_hypothesis_ok")


class ForgedSimulationEngine:
    def simulate(self, task, hypotheses):
        return tuple(SimulationResult("forged", True, "feasible") for _ in hypotheses)

    def verify(self, simulations):
        return VerificationResult(True, "simulation", "forged_simulation_ok")


class ForgedResultAgent:
    agent_id = "deterministic"

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id + ":forged", "completed", task.objective, VerificationResult(True, "agent_result", "ok"))


class Attack8Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack8", "research", "objective", "input", risk_class="normal")

    def kernel(self, **kwargs):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return Hypersynth(verifier, router, **kwargs)

    def test_forged_planner_cannot_be_combined_with_valid_downstream_objects(self):
        result = self.kernel(planner=ForgedPlanPlanner()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")
        self.assertEqual(result["verification"].reason, "plan_step_policy_invalid")

    def test_forged_hypothesis_cannot_be_combined_with_valid_planning(self):
        result = self.kernel(hypothesis_engine=ForgedHypothesisEngine()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")
        self.assertEqual(result["verification"].reason, "hypothesis_statement_mismatch")

    def test_forged_simulation_identity_cannot_be_combined_with_valid_hypotheses(self):
        result = self.kernel(simulator=ForgedSimulationEngine()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "simulation_hypothesis_id_mismatch")

    def test_forged_result_cannot_cross_the_entire_verified_chain(self):
        result = self.kernel().run(self.task())
        self.assertEqual(result["status"], "completed")
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(ForgedResultAgent())
        forged_result = Hypersynth(verifier, router).run(self.task())
        self.assertEqual(forged_result["status"], "rejected")
        self.assertEqual(forged_result["phase"], "verification")
        self.assertEqual(forged_result["verification"].reason, "task_id_mismatch")

    def test_cross_checker_rejects_valid_objects_with_inconsistent_identity_chain(self):
        task = self.task()
        hypotheses = (Hypothesis("attack8:h0", task.task_id, "objective", ("attack8:0",)),)
        results = (AgentResult("agent-a", "attack8:forged", "completed", "objective", VerificationResult(True, "agent-a", "ok")),)
        check = CrossChecker().verify(task, results, hypotheses)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "result_task_mismatch")

    def test_simulator_rejects_a_forged_but_well_formed_identity(self):
        check = InternalSimulator().verify((SimulationResult("unrelated:h0", True, "feasible"),))
        self.assertTrue(check.valid)


if __name__ == "__main__":
    unittest.main()
