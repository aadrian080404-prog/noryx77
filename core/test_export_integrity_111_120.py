import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.export_integrity_111_120 import ExportedIntegrityBoundary
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class ExportIntegrity111To120Tests(unittest.TestCase):
    STAGES = ExportedIntegrityBoundary.REQUIRED_STAGE_ORDER

    def setUp(self):
        self.crypto = CryptoIntegrity(b"z" * 32)
        self.task_id = "task-111-120"
        self.session_id = "session-111-120"
        self.risk = "normal"
        self.requirements = ("verify", "audit")
        self.payloads = tuple({"stage": stage, "value": i} for i, stage in enumerate(self.STAGES, 1))
        session = AttestationSession(
            self.crypto, self.task_id, self.risk, self.requirements,
            session_id=self.session_id,
        )
        self.context_tag = session.context_tag
        self.attestations = tuple(session.attest(stage, payload) for stage, payload in zip(self.STAGES, self.payloads))
        continuity = KernelContinuity(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, verification_requirements=self.requirements,
        )
        records = []
        evidence = []
        previous = ""
        for i, (stage, payload) in enumerate(zip(self.STAGES, self.payloads)):
            state = {"stage": stage, "value": i + 1}
            stage_input = {"stage": stage, "previous_continuity_tag": previous, "payload": payload}
            dependency = self.context_tag if i == 0 else self.attestations[i - 1].tag
            record = continuity.attest(stage, state, stage_input, payload, dependency_tag=dependency)
            records.append(record)
            evidence.append((stage, state, stage_input, payload, dependency))
            previous = record.tag
        self.records = tuple(records)
        self.evidence = tuple(evidence)
        policy = KernelContinuityPolicy(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            stage_order=self.STAGES,
        )
        self.seal = policy.seal(self.records)
        self.final_tag = HypersynthIntegrityVerifier.final_tag(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, requirements=self.requirements,
            stage_order=self.STAGES,
            stage_tags=tuple(x.tag for x in self.attestations),
            continuity_tags=tuple(x.tag for x in self.records),
            continuity_seal=self.seal.seal,
        )

    def verify(self, **changes):
        values = dict(
            crypto=self.crypto, session_id=self.session_id, context_tag=self.context_tag,
            task_id=self.task_id, risk_class=self.risk, requirements=self.requirements,
            attestations=self.attestations, payloads=self.payloads,
            continuity_records=self.records, continuity_evidence=self.evidence,
            continuity_seal=self.seal, final_continuity_tag=self.final_tag,
        )
        values.update(changes)
        return ExportedIntegrityBoundary.verify(**values)

    def test_attack111_wrong_key_rejected(self):
        self.assertFalse(self.verify(crypto=CryptoIntegrity(b"a" * 32)))

    def test_attack112_wrong_context_tag_rejected(self):
        self.assertFalse(self.verify(context_tag="0" * 64))

    def test_attack113_risk_substitution_rejected(self):
        self.assertFalse(self.verify(risk_class="high"))

    def test_attack114_requirement_substitution_rejected(self):
        self.assertFalse(self.verify(requirements=("different",)))

    def test_attack115_missing_continuity_evidence_is_rejected(self):
        self.assertFalse(self.verify(continuity_evidence=None))

    def test_attack116_attestation_payload_permutation_rejected(self):
        forged = list(self.payloads)
        forged[0], forged[1] = forged[1], forged[0]
        self.assertFalse(self.verify(payloads=tuple(forged)))

    def test_attack117_continuity_record_permutation_rejected(self):
        forged = list(self.records)
        forged[0], forged[1] = forged[1], forged[0]
        self.assertFalse(self.verify(continuity_records=tuple(forged)))

    def test_attack118_missing_or_extra_stage_rejected(self):
        self.assertFalse(self.verify(stage_order=self.STAGES[:-1]))
        self.assertFalse(self.verify(stage_order=self.STAGES + ("extra",)))

    def test_attack119_malformed_export_schema_rejected(self):
        self.assertFalse(self.verify(attestations=list(self.attestations)))
        self.assertFalse(self.verify(payloads=list(self.payloads)))
        self.assertFalse(self.verify(continuity_records=list(self.records)))
        self.assertFalse(self.verify(continuity_evidence=list(self.evidence)))

    def test_attack120_internal_record_tamper_cannot_hide_behind_valid_seal(self):
        forged = list(self.records)
        forged[4] = replace(forged[4], output_digest="0" * 64)
        self.assertFalse(self.verify(continuity_records=tuple(forged)))
        forged_seal = replace(self.seal, final_tag="0" * 64)
        self.assertFalse(self.verify(continuity_seal=forged_seal))
        self.assertTrue(self.verify())


if __name__ == "__main__":
    unittest.main()
