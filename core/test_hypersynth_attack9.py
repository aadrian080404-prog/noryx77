import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .reasoning import Hypothesis
from .router import ResourceRouter
from .verification import VerificationEngine


class RiskDowngradePlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "compute", "normal"),))

    def verify(self, plan, task):
        return VerificationResult(True, "plan", "planner_claimed_ok")


class RiskUpgradePlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "compute", "high"),))

    def verify(self, plan, task):
        return VerificationResult(True, "plan", "planner_claimed_ok")


class RequirementStrippingAgent:
    agent_id = "stripping-agent"

    def run(self, task):
        return AgentResult(self.agent_id, task.task_id, "completed", 123, VerificationResult(True, "agent_result", "claimed_ok"))


class Attack9Tests(unittest.TestCase):
    def task(self, *, risk="normal", requirements=()):
        return TaskSpec("attack9", "research", "objective", "input", verification_requirements=requirements, risk_class=risk)

    def kernel(self, **kwargs):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return Hypersynth(verifier, router, **kwargs)

    def test_task_continuity_rejects_risk_downgrade(self):
        verifier = VerificationEngine()
        parent = self.task(risk="high")
        child = TaskSpec("attack9:0", parent.task_type, parent.objective, parent.input, parent.constraints, parent.verification_requirements, "normal")
        check = verifier.verify_task_continuity(parent, child)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "child_risk_mismatch")

    def test_task_continuity_rejects_risk_upgrade(self):
        verifier = VerificationEngine()
        parent = self.task(risk="normal")
        child = TaskSpec("attack9:0", parent.task_type, parent.objective, parent.input, parent.constraints, parent.verification_requirements, "high")
        check = verifier.verify_task_continuity(parent, child)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "child_risk_mismatch")

    def test_forged_planner_cannot_downgrade_high_risk_task(self):
        result = self.kernel(planner=RiskDowngradePlanner()).run(self.task(risk="high"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")
        self.assertEqual(result["verification"].reason, "plan_step_risk_mismatch")

    def test_forged_planner_cannot_upgrade_normal_task(self):
        result = self.kernel(planner=RiskUpgradePlanner()).run(self.task(risk="normal"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "planning")
        self.assertEqual(result["verification"].reason, "plan_step_risk_mismatch")

    def test_derived_task_cannot_strip_verification_requirements(self):
        verifier = VerificationEngine()
        parent = self.task(requirements=("string",))
        child = TaskSpec("attack9:0", parent.task_type, parent.objective, parent.input, parent.constraints, (), parent.risk_class)
        check = verifier.verify_task_continuity(parent, child)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "child_verification_requirements_mismatch")

    def test_derived_task_cannot_substitute_verification_requirements(self):
        verifier = VerificationEngine()
        parent = self.task(requirements=("string",))
        child = TaskSpec("attack9:0", parent.task_type, parent.objective, parent.input, parent.constraints, ("non_empty",), parent.risk_class)
        check = verifier.verify_task_continuity(parent, child)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "child_verification_requirements_mismatch")

    def test_requirement_stripping_agent_cannot_complete(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(RequirementStrippingAgent())
        result = Hypersynth(verifier, router).run(self.task(requirements=("string",)))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "output_type_mismatch")

    def test_invalid_verification_requirement_is_rejected_at_task_boundary(self):
        result = self.kernel().run(self.task(requirements=("weaker-but-unknown",)))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "unsupported_verification_requirement")

    def test_task_continuity_preserves_identity_risk_and_requirements(self):
        verifier = VerificationEngine()
        parent = self.task(risk="sensitive", requirements=("string",))
        child = TaskSpec("attack9:0", parent.task_type, parent.objective, parent.input, parent.constraints, parent.verification_requirements, parent.risk_class)
        check = verifier.verify_task_continuity(parent, child)
        self.assertTrue(check.valid)
        self.assertEqual(check.reason, "task_continuity_ok")


if __name__ == "__main__":
    unittest.main()
