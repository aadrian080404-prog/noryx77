import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .reasoning import InternalSimulator
from .router import ResourceRouter
from .verification import VerificationEngine


class HypersynthVerifierBoundaryTests(unittest.TestCase):
    def task(self):
        return TaskSpec("boundary", "research", "analyze", "data", risk_class="normal")

    def router(self, verifier):
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return router

    def test_task_verifier_exception_fails_closed(self):
        class ExplodingVerifier(VerificationEngine):
            def verify_task(self, task):
                raise RuntimeError("verifier unavailable")

        verifier = ExplodingVerifier()
        result = Hypersynth(verifier, self.router(verifier)).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "task_verification_failure")

    def test_task_verifier_wrong_stage_is_rejected(self):
        class ForgedStageVerifier(VerificationEngine):
            def verify_task(self, task):
                return VerificationResult(True, "agent_result", "forged")

        verifier = ForgedStageVerifier()
        result = Hypersynth(verifier, self.router(verifier)).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "forged")

    def test_planner_verifier_wrong_stage_is_rejected(self):
        class ForgedPlanVerifier(VerificationEngine):
            def verify_task(self, task):
                return VerificationResult(True, "contract", "verified")

            def verify_output(self, output, *, stage="result"):
                if stage == "hypersynth_result":
                    return VerificationResult(True, "hypersynth_result", "verified")
                return super().verify_output(output, stage=stage)

        class ForgedPlanner:
            def build(self, task):
                from .planning import Plan, PlanStep
                return Plan(task.task_id, (PlanStep(f"{task.task_id}:0", task.objective, "compute", task.risk_class),))

            def verify(self, plan, task):
                return VerificationResult(True, "task", "forged_plan_stage")

        verifier = ForgedPlanVerifier()
        result = Hypersynth(verifier, self.router(verifier), planner=ForgedPlanner()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")
        self.assertEqual(result["verification"].reason, "forged_plan_stage")

    def test_hypothesis_verifier_wrong_stage_is_rejected(self):
        verifier = VerificationEngine()

        class ForgedHypothesisEngine:
            def generate(self, task, plan):
                from .reasoning import Hypothesis
                return (Hypothesis(f"{task.task_id}:h0", task.task_id, plan.steps[0].objective, (plan.steps[0].step_id,)),)

            def verify(self, hypotheses, task):
                return VerificationResult(True, "plan", "forged_hypothesis_stage")

        result = Hypersynth(
            verifier,
            self.router(verifier),
            hypothesis_engine=ForgedHypothesisEngine(),
        ).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")
        self.assertEqual(result["verification"].reason, "forged_hypothesis_stage")

    def test_simulation_verifier_wrong_stage_is_rejected(self):
        verifier = VerificationEngine()

        class ForgedSimulation(InternalSimulator):
            def verify(self, simulations):
                return VerificationResult(True, "plan", "forged_simulation_stage")

        result = Hypersynth(
            verifier,
            self.router(verifier),
            simulator=ForgedSimulation(),
        ).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "forged_simulation_stage")


if __name__ == "__main__":
    unittest.main()
