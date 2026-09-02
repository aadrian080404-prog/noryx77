import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.export_integrity_111_120 import ExportedIntegrityBoundary
from core.export_manifest_121_130 import ExportIntegrityManifest, IntegrityManifest
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class ExportManifest121To130Tests(unittest.TestCase):
    STAGES = ExportedIntegrityBoundary.REQUIRED_STAGE_ORDER

    def setUp(self):
        self.crypto = CryptoIntegrity(b"m" * 32)
        self.session_id = "session-121-130"
        self.task_id = "task-121-130"
        self.risk = "normal"
        self.requirements = ("verify", "audit")
        self.payloads = tuple({"stage": stage, "value": i} for i, stage in enumerate(self.STAGES, 1))
        session = AttestationSession(self.crypto, self.task_id, self.risk, self.requirements, session_id=self.session_id)
        self.context_tag = session.context_tag
        self.attestations = tuple(session.attest(stage, payload) for stage, payload in zip(self.STAGES, self.payloads))
        continuity = KernelContinuity(self.crypto, session_id=self.session_id, task_id=self.task_id,
                                     risk_class=self.risk, verification_requirements=self.requirements)
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
        policy = KernelContinuityPolicy(self.crypto, session_id=self.session_id, task_id=self.task_id, stage_order=self.STAGES)
        self.seal = policy.seal(self.records)
        self.final_tag = HypersynthIntegrityVerifier.final_tag(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, requirements=self.requirements, stage_order=self.STAGES,
            stage_tags=tuple(x.tag for x in self.attestations),
            continuity_tags=tuple(x.tag for x in self.records), continuity_seal=self.seal.seal,
        )
        self.manifest = ExportIntegrityManifest.create(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, requirements=self.requirements, stage_order=self.STAGES,
            attestations=self.attestations, payloads=self.payloads,
            continuity_records=self.records, continuity_evidence=self.evidence,
            continuity_seal=self.seal, final_continuity_tag=self.final_tag,
        )

    def verify(self, **changes):
        values = dict(
            crypto=self.crypto, manifest=self.manifest, session_id=self.session_id,
            task_id=self.task_id, risk_class=self.risk, requirements=self.requirements,
            stage_order=self.STAGES, attestations=self.attestations, payloads=self.payloads,
            continuity_records=self.records, continuity_evidence=self.evidence,
            continuity_seal=self.seal, final_continuity_tag=self.final_tag,
        )
        values.update(changes)
        return ExportIntegrityManifest.verify(**values)

    def test_attack121_payload_collection_substitution_is_rejected(self):
        forged = list(self.payloads)
        forged[0] = {"stage": "perception", "value": "substituted"}
        self.assertFalse(self.verify(payloads=tuple(forged)))

    def test_attack122_attestation_collection_substitution_is_rejected(self):
        forged = list(self.attestations)
        forged[3] = replace(forged[3], tag="0" * 64)
        self.assertFalse(self.verify(attestations=tuple(forged)))

    def test_attack123_continuity_record_substitution_is_rejected(self):
        forged = list(self.records)
        forged[5] = replace(forged[5], output_digest="0" * 64)
        self.assertFalse(self.verify(continuity_records=tuple(forged)))

    def test_attack124_continuity_evidence_substitution_is_rejected(self):
        forged = list(self.evidence)
        stage, state, stage_input, output, dependency = forged[2]
        forged[2] = (stage, state, stage_input, {"forged": True}, dependency)
        self.assertFalse(self.verify(continuity_evidence=tuple(forged)))

    def test_attack125_seal_substitution_is_rejected(self):
        forged = replace(self.seal, seal="0" * 64)
        self.assertFalse(self.verify(continuity_seal=forged))

    def test_attack126_final_tag_substitution_is_rejected(self):
        self.assertFalse(self.verify(final_continuity_tag="0" * 64))

    def test_attack127_manifest_identity_binding_is_rejected(self):
        self.assertFalse(self.verify(session_id="other-session"))
        self.assertFalse(self.verify(task_id="other-task"))
        self.assertFalse(self.verify(risk_class="high"))
        self.assertFalse(self.verify(requirements=("other",)))

    def test_attack128_stage_order_binding_is_rejected(self):
        forged = list(self.STAGES)
        forged[0], forged[1] = forged[1], forged[0]
        self.assertFalse(self.verify(stage_order=tuple(forged)))

    def test_attack129_manifest_algorithm_and_version_tampering_is_rejected(self):
        self.assertFalse(self.verify(manifest=replace(self.manifest, algorithm="SHA-256")))
        self.assertFalse(self.verify(manifest=replace(self.manifest, version=2)))

    def test_attack130_manifest_tag_and_key_tampering_is_rejected(self):
        self.assertFalse(self.verify(manifest=replace(self.manifest, tag="0" * 64)))
        self.assertFalse(self.verify(crypto=CryptoIntegrity(b"x" * 32)))
        self.assertTrue(self.verify())
        self.assertIsInstance(self.manifest, IntegrityManifest)


if __name__ == "__main__":
    unittest.main()
