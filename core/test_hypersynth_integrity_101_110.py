import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class HypersynthIntegrity101To110Tests(unittest.TestCase):
    STAGES = (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )

    def setUp(self):
        self.crypto = CryptoIntegrity(b"y" * 32)
        self.task_id = "task-101-110"
        self.session_id = "session-101-110"
        self.risk = "normal"
        self.requirements = ("verify", "audit")
        self.payloads = tuple({"stage": stage, "value": index} for index, stage in enumerate(self.STAGES, 1))
        session = AttestationSession(
            self.crypto, self.task_id, self.risk, self.requirements,
            session_id=self.session_id,
        )
        self.context_tag = session.context_tag
        self.attestations = tuple(
            session.attest(stage, payload)
            for stage, payload in zip(self.STAGES, self.payloads)
        )
        continuity = KernelContinuity(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, verification_requirements=self.requirements,
        )
        previous = ""
        records = []
        evidence = []
        for index, (stage, payload) in enumerate(zip(self.STAGES, self.payloads)):
            state = {"stage": stage, "value": payload["value"]}
            stage_input = {
                "stage": stage,
                "previous_continuity_tag": previous,
                "payload": payload,
            }
            dependency = self.context_tag if index == 0 else self.attestations[index - 1].tag
            record = continuity.attest(
                stage, state, stage_input, payload, dependency_tag=dependency
            )
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
            self.crypto,
            session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, requirements=self.requirements,
            stage_order=self.STAGES,
            stage_tags=tuple(item.tag for item in self.attestations),
            continuity_tags=tuple(item.tag for item in self.records),
            continuity_seal=self.seal.seal,
        )

    def verify(self, **overrides):
        values = dict(
            crypto=self.crypto,
            session_id=self.session_id,
            task_id=self.task_id,
            risk_class=self.risk,
            requirements=self.requirements,
            stage_order=self.STAGES,
            attestations=self.attestations,
            payloads=self.payloads,
            continuity_records=self.records,
            continuity_seal=self.seal,
            final_continuity_tag=self.final_tag,
            context_tag=self.context_tag,
            continuity_evidence=self.evidence,
        )
        values.update(overrides)
        return HypersynthIntegrityVerifier.verify_exported_integrity(**values)

    def test_attack101_exported_integrity_is_independent_of_local_policy_state(self):
        self.assertTrue(
            HypersynthIntegrityVerifier.verify_exported_integrity(
                self.crypto,
                session_id=self.session_id,
                task_id=self.task_id,
                risk_class=self.risk,
                requirements=self.requirements,
                stage_order=self.STAGES,
                attestations=self.attestations,
                payloads=self.payloads,
                continuity_records=self.records,
                continuity_seal=self.seal,
                final_continuity_tag=self.final_tag,
                context_tag=self.context_tag,
                continuity_evidence=self.evidence,
            )
        )

    def test_attack102_cross_session_final_tag_replay_rejected(self):
        self.assertFalse(self.verify(session_id="other-session"))

    def test_attack103_cross_task_final_tag_replay_rejected(self):
        self.assertFalse(self.verify(task_id="other-task"))

    def test_attack104_stage_order_fork_rejected_by_attestation_and_continuity_binding(self):
        forged_order = self.STAGES[:4] + ("allocation", "simulation", "hypothesis", "verification", "metacognition")
        self.assertFalse(self.verify(stage_order=forged_order))

    def test_attack105_every_continuity_record_field_tamper_is_detected(self):
        fields = (
            "task_id", "stage", "sequence", "state_digest", "input_digest",
            "output_digest", "dependency_tag", "previous_tag", "tag",
        )
        replacements = {
            "task_id": "foreign-task", "stage": "foreign-stage", "sequence": 77,
            "state_digest": "0" * 64, "input_digest": "0" * 64,
            "output_digest": "0" * 64, "dependency_tag": "0" * 64,
            "previous_tag": "0" * 64, "tag": "0" * 64,
        }
        for record_index in range(len(self.records)):
            for field in fields:
                with self.subTest(record=record_index, field=field):
                    forged = list(self.records)
                    forged[record_index] = replace(
                        forged[record_index], **{field: replacements[field]}
                    )
                    self.assertFalse(self.verify(continuity_records=tuple(forged)))

    def test_attack106_exported_evidence_is_immutable_and_reverification_survives_copying(self):
        copied_attestations = tuple(replace(item) for item in self.attestations)
        copied_records = tuple(replace(item) for item in self.records)
        self.assertTrue(
            self.verify(
                attestations=copied_attestations,
                continuity_records=copied_records,
            )
        )
        with self.assertRaises(TypeError):
            self.attestations[0] = copied_attestations[0]
        with self.assertRaises(TypeError):
            self.records[0] = copied_records[0]

    def test_attack107_attestation_continuity_and_final_domains_are_distinct(self):
        material = {"task_id": self.task_id, "stage": "planning", "value": 1}
        self.assertNotEqual(
            self.crypto.digest("hypersynth_stage", material),
            self.crypto.digest("kernel_continuity", material),
        )
        self.assertNotEqual(
            self.crypto.digest("kernel_continuity", material),
            self.crypto.digest("hypersynth_final_continuity", material),
        )

    def test_attack108_non_finite_nested_payload_is_rejected_fail_closed(self):
        poisoned = list(self.payloads)
        poisoned[3] = {"stage": "hypothesis", "nested": {"x": float("nan")}}
        self.assertFalse(self.verify(payloads=tuple(poisoned)))

    def test_attack109_any_exported_integrity_failure_prevents_success_verdict(self):
        forged = replace(self.seal, final_tag="0" * 64)
        self.assertFalse(self.verify(continuity_seal=forged))
        self.assertFalse(self.verify(final_continuity_tag="0" * 64))
        forged_records = list(self.records)
        forged_records[-1] = replace(forged_records[-1], output_digest="0" * 64)
        self.assertFalse(self.verify(continuity_records=tuple(forged_records)))

    def test_attack110_end_to_end_single_field_tampering_across_all_nine_stages(self):
        for index in range(len(self.STAGES)):
            forged_attestations = list(self.attestations)
            forged_attestations[index] = replace(
                forged_attestations[index], payload_digest="0" * 64
            )
            with self.subTest(stage=self.STAGES[index], tamper="attestation"):
                self.assertFalse(self.verify(attestations=tuple(forged_attestations)))

            forged_evidence = list(self.evidence)
            stage, state, stage_input, output, dependency = forged_evidence[index]
            forged_evidence[index] = (
                stage, {**state, "tampered": True}, stage_input, output, dependency
            )
            with self.subTest(stage=self.STAGES[index], tamper="state"):
                self.assertFalse(self.verify(continuity_evidence=tuple(forged_evidence)))


if __name__ == "__main__":
    unittest.main()
