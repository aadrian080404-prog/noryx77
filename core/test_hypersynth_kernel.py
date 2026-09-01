import unittest

from core.contracts import AgentResult, TaskSpec, VerificationResult
from core.hypersynth import Hypersynth
from core.hypersynth_kernel import AttestedHypersynthKernel
from core.planning import Plan, PlanStep
from core.router import ResourceRouter
from core.agents import Agent
from core.verification import VerificationEngine
from core.attestation_session import AttestationSession


class KernelPlanner:
    def build(self, task):
        return Plan(task.task_id, (PlanStep(task.task_id + ":0", task.objective),))

    def verify(self, plan, task):
        return VerificationResult(True, "plan", "ok")


class KernelAgent(Agent):
    def __init__(self, agent_id, verifier):
        self.agent_id = agent_id
        self.verifier = verifier

    def run(self, task):
        output = task.objective
        return AgentResult(self.agent_id, task.task_id, "completed", output,
                           self.verifier.verify_output(output, stage="agent_result"))


class AttestedKernelTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.router = ResourceRouter()
        self.router.register(KernelAgent("agent-a", self.verifier))

    def make_task(self, task_id="kernel"):
        return TaskSpec(task_id, "research", "verified kernel result", "input", risk_class="normal")

    def test_attested_kernel_executes_and_verifies_full_chain(self):
        kernel = Hypersynth(self.verifier, self.router, planner=KernelPlanner(), max_agents=1)
        attested = AttestedHypersynthKernel(kernel, crypto=None)
        result = attested.run(self.make_task())
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["attestation_verified"])
        self.assertEqual(len(result["attestations"]), 9)
        self.assertEqual(tuple(item.stage for item in result["attestations"]), AttestedHypersynthKernel.STAGE_ORDER)
        self.assertTrue(isinstance(result["attestation_session_id"], str))
        self.assertEqual(len(result["attestation_context_tag"]), 64)

    def test_tampering_with_attested_stage_payload_is_rejected(self):
        kernel = Hypersynth(self.verifier, self.router, planner=KernelPlanner(), max_agents=1)
        attested = AttestedHypersynthKernel(kernel)
        result = attested.run(self.make_task("tamper"))
        chain = result["attestations"]
        session = AttestationSession(attested.attestation.crypto, "tamper", "normal", ())
        payloads = [attested._payload(result, stage) for stage in attested.STAGE_ORDER]
        payloads[5] = {"agent": "forged-agent"}
        # A completed run's attestation chain is bound to its original random session.
        self.assertFalse(session.verify(chain[5], "allocation", payloads[5], consume=False))

    def test_rejected_kernel_does_not_claim_attestation_success(self):
        class RejectingPlanner(KernelPlanner):
            def verify(self, plan, task):
                return VerificationResult(False, "planning", "planner_rejected")

        kernel = Hypersynth(self.verifier, self.router, planner=RejectingPlanner(), max_agents=1)
        result = AttestedHypersynthKernel(kernel).run(self.make_task("rejected"))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["attestations"], ())
        self.assertNotIn("attestation_verified", result)

    def test_non_finite_evidence_is_rejected(self):
        with self.assertRaises(TypeError):
            AttestedHypersynthKernel._canonical(float("nan"))

    def test_kernel_constructor_rejects_wrong_kernel_type(self):
        with self.assertRaises(TypeError):
            AttestedHypersynthKernel(object())


if __name__ == "__main__":
    unittest.main()
