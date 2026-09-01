import unittest

from core.attestation import StageAttestation
from core.attestation_session import AttestationSession, SessionContext
from core.crypto import CryptoIntegrity


class Attack61To70Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"s" * 32)
        self.session = AttestationSession(self.crypto, "task-61", "normal", ("string",), session_id="session-61")

    def test_attack61_session_context_is_authenticated(self):
        self.assertTrue(self.session.verify_context(self.session.context))
        forged = SessionContext("session-61", "task-foreign", "normal", ("string",))
        self.assertFalse(self.session.verify_context(forged))

    def test_attack62_session_context_tag_cannot_be_forged(self):
        original = self.session.context_tag
        self.session._context_tag = "0" * 64
        self.assertFalse(self.session.verify_context(self.session.context))
        self.session._context_tag = original

    def test_attack63_stage_is_bound_to_session_context(self):
        attestation = self.session.attest("planning", {"step": "task-61:0"})
        self.assertTrue(self.session.verify(attestation, "planning", {"step": "task-61:0"}, consume=False))
        self.assertFalse(self.session.verify(attestation, "planning", {"step": "task-61:1"}, consume=False))

    def test_attack64_stage_name_swap_is_rejected(self):
        attestation = self.session.attest("planning", {"step": "x"})
        self.assertFalse(self.session.verify(attestation, "execution", {"step": "x"}, consume=False))

    def test_attack65_cross_task_attestation_is_rejected(self):
        attestation = self.session.attest("planning", {"step": "x"})
        foreign = AttestationSession(self.crypto, "task-foreign", "normal", ("string",), session_id="session-foreign")
        self.assertFalse(foreign.verify(attestation, "planning", {"step": "x"}, consume=False))

    def test_attack66_cross_risk_attestation_is_rejected(self):
        attestation = self.session.attest("planning", {"step": "x"})
        foreign = AttestationSession(self.crypto, "task-61", "high", ("string",), session_id="session-high")
        self.assertFalse(foreign.verify(attestation, "planning", {"step": "x"}, consume=False))

    def test_attack67_cross_requirement_attestation_is_rejected(self):
        attestation = self.session.attest("planning", {"step": "x"})
        foreign = AttestationSession(self.crypto, "task-61", "normal", (), session_id="session-empty")
        self.assertFalse(foreign.verify(attestation, "planning", {"step": "x"}, consume=False))

    def test_attack68_consumed_attestation_cannot_be_replayed(self):
        attestation = self.session.attest("planning", {"step": "x"})
        self.assertTrue(self.session.verify(attestation, "planning", {"step": "x"}))
        self.assertFalse(self.session.verify(attestation, "planning", {"step": "x"}))

    def test_attack69_closed_session_rejects_new_evidence(self):
        self.session.close()
        with self.assertRaisesRegex(RuntimeError, "attestation_session_closed"):
            self.session.attest("planning", {"step": "x"})

    def test_attack70_closed_session_rejects_verification(self):
        attestation = self.session.attest("planning", {"step": "x"})
        self.session.close()
        self.assertFalse(self.session.verify(attestation, "planning", {"step": "x"}))

    def test_malformed_attestation_fails_closed(self):
        forged = StageAttestation("task-61", "planning", 1, "normal", ("string",), "0" * 64, "", "0" * 64)
        self.assertFalse(self.session.verify(forged, "planning", {"step": "x"}, consume=False))


if __name__ == "__main__":
    unittest.main()
