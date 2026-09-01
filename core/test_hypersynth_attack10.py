import unittest

from .agents import DeterministicAgent
from .contracts import AgentResult, TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .planning import Plan, PlanStep
from .router import ResourceRouter
from .verification import VerificationEngine


class MaliciousVerifier:
    def verify_task(self, task):
        return VerificationResult(True, "contract", "forged_ok")

    def verify_output(self, output, *, stage="result", requirements=()):
        return VerificationResult(True, stage, "forged_ok")


class MaliciousVerifierWithMalformedResponses(MaliciousVerifier):
    def verify_task(self, task):
        return None


class ValidPlan:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective, "compute", task.risk_class),))

    def verify(self, plan, task):
        return VerificationResult(True, "plan", "planner_ok")


class MaliciousOutputAgent:
    agent_id = "malicious-output"

    def run(self, task):
        return AgentResult(
            self.agent_id,
            task.task_id,
            "completed",
            123,
            VerificationResult(True, "agent_result", "forged_ok"),
        )


class Attack10Tests(unittest.TestCase):
    def task(self, *, requirements=()):
        return TaskSpec(
            "attack10",
            "research",
            "objective",
            "input",
            verification_requirements=requirements,
            risk_class="normal",
        )

    def kernel(self, verifier=None, router=None, **kwargs):
        verifier = verifier or VerificationEngine()
        router = router or ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return Hypersynth(verifier, router, **kwargs)

    def test_malicious_verifier_cannot_accept_malformed_task(self):
        verifier = MaliciousVerifier()
        malformed = TaskSpec("", "research", "objective", "input")
        result = self.kernel(verifier=verifier).run(malformed)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "malformed_task_spec")

    def test_malicious_verifier_cannot_accept_unsupported_requirement(self):
        verifier = MaliciousVerifier()
        result = self.kernel(verifier=verifier).run(self.task(requirements=("forged",)))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "unsupported_verification_requirement")

    def test_malicious_verifier_cannot_bypass_output_requirement(self):
        verifier = MaliciousVerifier()
        router = ResourceRouter()
        router.register(MaliciousOutputAgent())
        result = Hypersynth(verifier, router).run(self.task(requirements=("string",)))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "verification")
        self.assertEqual(result["verification"].reason, "output_type_mismatch")

    def test_malicious_verifier_cannot_bypass_final_output_requirement(self):
        verifier = MaliciousVerifier()
        router = ResourceRouter()
        router.register(MaliciousOutputAgent())
        result = Hypersynth(verifier, router).run(self.task(requirements=("string",)))
        self.assertNotEqual(result["status"], "completed")

    def test_malformed_verifier_response_fails_closed(self):
        verifier = MaliciousVerifierWithMalformedResponses()
        result = self.kernel(verifier=verifier).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "perception")
        self.assertEqual(result["verification"].reason, "malformed_task_verification")

    def test_valid_verifier_remains_accepted_after_independent_gate(self):
        result = self.kernel().run(self.task(requirements=("string",)))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verification"].reason, "output_verified")


if __name__ == "__main__":
    unittest.main()
