import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.export_manifest_121_130 import ExportIntegrityManifest
from core.export_manifest_boundary_131_140 import ExportManifestAcceptanceBoundary
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class ExportManifestBoundary131To140Tests(unittest.TestCase):
    STAGES = ExportManifestAcceptanceBoundary.STAGE_ORDER

    def setUp(self):
        self.crypto = CryptoIntegrity(b"n" * 32)
        self.session_id = "session-131-140"
        self.task_id = "task-131-140"
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
            context_tag=self.context_tag,
        )
        values.update(changes)
        return ExportManifestAcceptanceBoundary.verify(**values)

    def test_attack131_manifest_replay_across_sessions_is_rejected(self):
        other = AttestationSession(self.crypto, self.task_id, self.risk, self.requirements, session_id="other-session-131")
        other_context = other.context_tag
        self.assertFalse(self.verify(session_id="other-session-131", context_tag=other_context))

    def test_attack132_manifest_replay_across_tasks_is_rejected(self):
        self.assertFalse(self.verify(task_id="other-task-132"))

    def test_attack133_cross_risk_manifest_substitution_is_rejected(self):
        self.assertFalse(self.verify(risk_class="high"))

    def test_attack134_cross_requirement_manifest_substitution_is_rejected(self):
        self.assertFalse(self.verify(requirements=("different-requirement",)))

    def test_attack135_valid_signed_collection_swap_is_rejected(self):
        other_payloads = tuple({"stage": stage, "value": i + 100} for i, stage in enumerate(self.STAGES))
        self.assertFalse(self.verify(payloads=other_payloads))
        forged = replace(self.manifest, tag=self.manifest.tag)
        self.assertFalse(self.verify(manifest=forged, payloads=other_payloads))

    def test_attack136_stale_manifest_against_newer_evidence_is_rejected(self):
        newer = list(self.payloads)
        newer[7] = {"stage": "verification", "value": 999}
        self.assertFalse(self.verify(payloads=tuple(newer)))

    def test_attack137_partial_manifest_fields_fail_closed(self):
        self.assertFalse(self.verify(manifest=replace(self.manifest, final_continuity_tag="")))
        self.assertFalse(self.verify(manifest=replace(self.manifest, tag="")))

    def test_attack138_duplicate_or_ambiguous_stage_identity_is_rejected(self):
        duplicate_order = list(self.STAGES)
        duplicate_order[-1] = duplicate_order[-2]
        self.assertFalse(self.verify(stage_order=tuple(duplicate_order)))
        forged_payloads = list(self.payloads)
        forged_payloads[4] = {"stage": "planning", "value": 5}
        self.assertFalse(self.verify(payloads=tuple(forged_payloads)))

    def test_attack139_mutation_after_verification_is_not_trusted(self):
        self.assertTrue(self.verify())
        mutable_state = list(self.evidence)
        stage, state, stage_input, output, dependency = mutable_state[0]
        state["value"] = 777
        self.assertFalse(self.verify(continuity_evidence=tuple(mutable_state)))

    def test_attack140_forged_manifest_cannot_hide_behind_local_success(self):
        forged = replace(self.manifest, tag="0" * 64)
        self.assertFalse(self.verify(manifest=forged))
        self.assertTrue(self.verify())


if __name__ == "__main__":
    unittest.main()
