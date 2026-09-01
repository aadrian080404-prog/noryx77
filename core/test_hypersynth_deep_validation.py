import unittest

from .agents import Agent, DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine


class TwoStepPlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective), PlanStep(task.task_id + ":1", task.objective)))

    def verify(self, plan, task):
        return VerificationResult(plan.task_id == task.task_id and len(plan.steps) == 2, "plan", "plan_ok")


class IdentityTamperAgent(Agent):
    agent_id = "honest-agent"

    def run(self, task):
        return AgentResult("forged-agent", task.task_id, "completed", task.objective, VerificationResult(True, "result", "ok"))


class MalformedStatusAgent(Agent):
    agent_id = "status-agent"

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id, "running", task.objective, VerificationResult(True, "result", "ok"))


class StageTamperAgent(Agent):
    agent_id = "stage-agent"

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id, "completed", task.objective, VerificationResult(True, "forged-stage", "ok"))


class DeepValidationTests(unittest.TestCase):
    def task(self, **changes):
        values = dict(task_id="deep", task_type="research", objective="verified objective", input="controlled input", risk_class="normal")
        values.update(changes)
        return TaskSpec(**values)

    def kernel(self, agent):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(agent)
        return Hypersynth(verifier, router, max_agents=1)

    def test_success_confidence_is_evidence_backed(self):
        kernel = self.kernel(DeterministicAgent(VerificationEngine()))
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["reflection"]["evidence_count"], 9)
        self.assertEqual(result["reflection"]["evidence_required"], 9)
        self.assertEqual(result["reflection"]["confidence"], 1.0)
        self.assertEqual(result["state"].confidence, 1.0)

    def test_identity_tampering_is_rejected_independently(self):
        result = self.kernel(IdentityTamperAgent()).run(self.task(task_id="identity"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "agent_id_mismatch")

    def test_status_tampering_is_rejected(self):
        result = self.kernel(MalformedStatusAgent()).run(self.task(task_id="status"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "agent_not_completed")

    def test_verification_stage_tampering_is_rejected(self):
        result = self.kernel(StageTamperAgent()).run(self.task(task_id="stage"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "verification_identity_mismatch")

    def test_multistep_results_are_verified_against_matching_assignment(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        kernel = Hypersynth(verifier, router, planner=TwoStepPlanner(), max_agents=2)
        result = kernel.run(self.task(task_id="multi"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(tuple(r.task_id for r in result["results"]), ("multi:0", "multi:1"))
        self.assertEqual(result["reflection"]["evidence_count"], 9)

    def test_phase_gate_rejects_non_sequential_transition(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        kernel = Hypersynth(verifier, router)
        task = self.task(task_id="phase")
        check = kernel._advance_phase(0, "planning", task)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "phase_order_violation")


if __name__ == "__main__":
    unittest.main()
