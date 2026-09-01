import unittest

from core.attestation import HypersynthAttestation, StageAttestation
from core.crypto import CryptoIntegrity


def handler_a(value):
    return value + 1


def handler_b(value):
    return value + 2


class HypersynthAttestationAttackTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)
        self.att = HypersynthAttestation(self.crypto)

    def test_attack51_handler_swap_is_rejected(self):
        cap = self.att.attest_capability("compute", "normal", handler_a)
        self.assertTrue(self.att.verify_capability(cap, handler_a, risk_class="normal"))
        self.assertFalse(self.att.verify_capability(cap, handler_b, risk_class="normal"))

    def test_attack52_revoked_capability_is_rejected(self):
        cap = self.att.attest_capability("compute", "normal", handler_a)
        token = self.att.revoke_capability("compute", "security policy")
        self.assertEqual(len(token), 64)
        self.assertTrue(self.att.is_revoked("compute", "security policy"))
        self.assertFalse(self.att.verify_capability(cap, handler_a, risk_class="normal"))

    def test_attack53_sequence_exhaustion_is_fail_closed(self):
        self.att._sequence = HypersynthAttestation.MAX_SEQUENCE
        with self.assertRaises(OverflowError):
            self.att.attest_stage("task-1", "planning", "normal", (), {"x": 1})

    def test_attack54_task_risk_and_requirements_are_bound(self):
        original = self.att.attest_stage("task-1", "planning", "normal", ("string",), {"x": 1})
        self.assertFalse(self.att.verify_stage(StageAttestation(
            original.task_id, original.stage, original.sequence, "high",
            original.verification_requirements, original.payload_digest,
            original.previous_tag, original.tag), {"x": 1}))
        self.assertFalse(self.att.verify_stage(StageAttestation(
            original.task_id, original.stage, original.sequence, original.risk_class,
            (), original.payload_digest, original.previous_tag, original.tag), {"x": 1}))

    def test_attack55_stage_domain_binding(self):
        original = self.att.attest_stage("task-1", "planning", "normal", (), {"x": 1})
        forged = StageAttestation("task-1", "execution", original.sequence, "normal", (), original.payload_digest, original.previous_tag, original.tag)
        self.assertFalse(self.att.verify_stage(forged, {"x": 1}))

    def test_attack56_plan_payload_tamper_is_rejected(self):
        original = self.att.attest_stage("task-1", "planning", "normal", (), {"steps": ["task-1:1"]})
        self.assertFalse(self.att.verify_stage(original, {"steps": ["task-1:2"]}))

    def test_attack57_hypothesis_payload_tamper_is_rejected(self):
        original = self.att.attest_stage("task-1", "hypothesis", "normal", (), {"hypothesis": "task-1:1"})
        self.assertFalse(self.att.verify_stage(original, {"hypothesis": "task-1:2"}))

    def test_attack58_simulation_payload_tamper_is_rejected(self):
        original = self.att.attest_stage("task-1", "simulation", "normal", (), {"feasible": True})
        self.assertFalse(self.att.verify_stage(original, {"feasible": False}))

    def test_attack59_agent_result_attestation_binds_agent_stage(self):
        original = self.att.attest_stage("task-1", "agent_result:agent-a", "normal", (), {"status": "completed", "output": "ok"})
        forged = StageAttestation("task-1", "agent_result:agent-b", original.sequence, "normal", (), original.payload_digest, original.previous_tag, original.tag)
        self.assertFalse(self.att.verify_stage(forged, {"status": "completed", "output": "ok"}))
        self.assertTrue(self.att.verify_stage(original, {"status": "completed", "output": "ok"}))

    def test_attack60_final_pipeline_chain_binds_every_stage(self):
        stages = (("planning", {"step": "1"}), ("hypothesis", {"h": "1"}), ("simulation", {"feasible": True}), ("execution", {"agent": "a"}), ("verification", {"valid": True}), ("metacognition", {"confidence": 1.0}))
        attestations = self.att.attest_pipeline("task-1", "normal", (), stages)
        payloads = tuple(payload for _, payload in stages)
        self.assertTrue(self.att.verify_pipeline(attestations, payloads, "task-1", "normal", ()))
        tampered = list(payloads)
        tampered[2] = {"feasible": False}
        self.assertFalse(self.att.verify_pipeline(attestations, tuple(tampered), "task-1", "normal", ()))

    def test_pipeline_sequence_and_previous_tag_cannot_be_swapped(self):
        stages = (("planning", {"step": "1"}), ("hypothesis", {"h": "1"}))
        attestations = self.att.attest_pipeline("task-1", "normal", (), stages)
        swapped = (attestations[1], attestations[0])
        self.assertFalse(self.att.verify_pipeline(swapped, tuple(x[1] for x in stages), "task-1", "normal", ()))

    def test_capability_version_binding(self):
        cap = self.att.attest_capability("compute", "normal", handler_a, version=1)
        forged = type(cap)(cap.capability, cap.risk_class, cap.handler_fingerprint, 2, cap.tag)
        self.assertFalse(self.att.verify_capability(forged, handler_a))

    def test_revocation_reason_is_authenticated(self):
        self.att.attest_capability("compute", "normal", handler_a)
        self.att.revoke_capability("compute", "approved")
        self.assertFalse(self.att.is_revoked("compute", "forged"))


if __name__ == "__main__":
    unittest.main()
