import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.export_acceptance_141_150 import AcceptanceReceipt, ExportAcceptanceController
from core.export_manifest_121_130 import ExportIntegrityManifest
from core.export_manifest_boundary_131_140 import ExportManifestAcceptanceBoundary
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class ExportAcceptance141To150Tests(unittest.TestCase):
    STAGES = ExportManifestAcceptanceBoundary.STAGE_ORDER

    def setUp(self):
        self.crypto = CryptoIntegrity(b"a" * 32)
        self.session_id = "session-141-150"
        self.task_id = "task-141-150"
        self.risk = "normal"
        self.requirements = ("verify", "audit")
        self.payloads = tuple({"stage": stage, "value": i} for i, stage in enumerate(self.STAGES, 1))
        session = AttestationSession(self.crypto, self.task_id, self.risk, self.requirements, session_id=self.session_id)
        self.context_tag = session.context_tag
        self.attestations = tuple(session.attest(stage, payload) for stage, payload in zip(self.STAGES, self.payloads))
        continuity = KernelContinuity(self.crypto, session_id=self.session_id, task_id=self.task_id,
                                     risk_class=self.risk, verification_requirements=self.requirements)
        records, evidence, previous = [], [], ""
        for i, (stage, payload) in enumerate(zip(self.STAGES, self.payloads)):
            state = {"stage": stage, "value": i + 1}
            stage_input = {"stage": stage, "previous_continuity_tag": previous, "payload": payload}
            dependency = self.context_tag if i == 0 else self.attestations[i - 1].tag
            record = continuity.attest(stage, state, stage_input, payload, dependency_tag=dependency)
            records.append(record); evidence.append((stage, state, stage_input, payload, dependency)); previous = record.tag
        self.records, self.evidence = tuple(records), tuple(evidence)
        policy = KernelContinuityPolicy(self.crypto, session_id=self.session_id, task_id=self.task_id, stage_order=self.STAGES)
        self.seal = policy.seal(self.records)
        self.final_tag = HypersynthIntegrityVerifier.final_tag(
            self.crypto, session_id=self.session_id, task_id=self.task_id, risk_class=self.risk,
            requirements=self.requirements, stage_order=self.STAGES,
            stage_tags=tuple(x.tag for x in self.attestations), continuity_tags=tuple(x.tag for x in self.records),
            continuity_seal=self.seal.seal)
        self.manifest = ExportIntegrityManifest.create(
            self.crypto, session_id=self.session_id, task_id=self.task_id, risk_class=self.risk,
            requirements=self.requirements, stage_order=self.STAGES, attestations=self.attestations,
            payloads=self.payloads, continuity_records=self.records, continuity_evidence=self.evidence,
            continuity_seal=self.seal, final_continuity_tag=self.final_tag)
        self.values = dict(
            session_id=self.session_id, task_id=self.task_id, risk_class=self.risk,
            requirements=self.requirements, stage_order=self.STAGES, attestations=self.attestations,
            payloads=self.payloads, continuity_records=self.records, continuity_evidence=self.evidence,
            continuity_seal=self.seal, final_continuity_tag=self.final_tag, context_tag=self.context_tag)
        self.controller = ExportAcceptanceController(self.crypto)

    def accept(self, controller=None, **changes):
        values = dict(self.values); values.update(changes)
        return (controller or self.controller).accept(self.manifest, **values)

    def test_attack141_exact_manifest_replay_is_rejected(self):
        receipt = self.accept()
        self.assertIsInstance(receipt, AcceptanceReceipt)
        self.assertIsNone(self.accept())
        self.assertTrue(self.controller.accepted(self.manifest.tag))

    def test_attack142_replay_survives_controller_reconstruction_with_same_crypto(self):
        self.assertIsNotNone(self.accept())
        other = ExportAcceptanceController(self.crypto)
        self.assertIsNone(self.accept(controller=other))

    def test_attack143_receipt_tag_tampering_is_rejected(self):
        receipt = self.accept()
        forged = replace(receipt, receipt_tag="0" * 64)
        self.assertFalse(self.controller.verify_receipt(forged, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class=self.risk))

    def test_attack144_receipt_session_substitution_is_rejected(self):
        receipt = self.accept()
        self.assertFalse(self.controller.verify_receipt(receipt, manifest_tag=self.manifest.tag,
                                                        session_id="other-session", task_id=self.task_id, risk_class=self.risk))

    def test_attack145_receipt_task_substitution_is_rejected(self):
        receipt = self.accept()
        self.assertFalse(self.controller.verify_receipt(receipt, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id="other-task", risk_class=self.risk))

    def test_attack146_receipt_risk_substitution_is_rejected(self):
        receipt = self.accept()
        self.assertFalse(self.controller.verify_receipt(receipt, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class="high"))

    def test_attack147_receipt_counter_substitution_is_rejected(self):
        receipt = self.accept()
        forged = replace(receipt, counter=1)
        self.assertFalse(self.controller.verify_receipt(forged, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class=self.risk))

    def test_attack148_receipt_nonce_substitution_is_rejected(self):
        receipt = self.accept()
        forged = replace(receipt, nonce="f" * 64)
        self.assertFalse(self.controller.verify_receipt(forged, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class=self.risk))

    def test_attack149_local_acceptance_cache_reset_cannot_replay_crypto_state(self):
        self.assertIsNotNone(self.accept())
        self.controller._accepted.clear()
        self.controller._receipts.clear()
        self.assertIsNone(self.accept())

    def test_attack150_malformed_or_wrong_type_receipt_fails_closed(self):
        self.assertFalse(self.controller.verify_receipt("not-a-receipt", manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class=self.risk))
        malformed = AcceptanceReceipt("bad", 1, "x", 0, self.manifest.tag,
                                      self.session_id, self.task_id, self.risk, "0" * 64)
        self.assertFalse(self.controller.verify_receipt(malformed, manifest_tag=self.manifest.tag,
                                                        session_id=self.session_id, task_id=self.task_id, risk_class=self.risk))


if __name__ == "__main__":
    unittest.main()
