import unittest
from dataclasses import replace

from core.attestation_session import AttestationSession
from core.crypto import CryptoIntegrity
from core.hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from core.kernel_continuity import KernelContinuity
from core.kernel_continuity_81_90 import KernelContinuityPolicy


class HypersynthIntegrity91To100Tests(unittest.TestCase):
    STAGES = (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )

    def setUp(self):
        self.crypto = CryptoIntegrity(b"z" * 32)
        self.task_id = "task-91-100"
        self.session_id = "session-91-100"
        self.risk = "normal"
        self.requirements = ("verify",)
        self.payloads = tuple({"stage": stage, "value": index} for index, stage in enumerate(self.STAGES, 1))
        session = AttestationSession(self.crypto, self.task_id, self.risk, self.requirements, session_id=self.session_id)
        self.context_tag = session.context_tag
        self.attestations = tuple(session.attest(stage, payload) for stage, payload in zip(self.STAGES, self.payloads))
        continuity = KernelContinuity(self.crypto, session_id=self.session_id, task_id=self.task_id,
                                     risk_class=self.risk, verification_requirements=self.requirements)
        previous = ""
        records = []
        for index, (stage, payload) in enumerate(zip(self.STAGES, self.payloads)):
            state = {"stage": stage, "value": payload["value"]}
            stage_input = {"stage": stage, "previous_continuity_tag": previous, "payload": payload}
            dependency = self.context_tag if index == 0 else self.attestations[index - 1].tag
            record = continuity.attest(stage, state, stage_input, payload, dependency_tag=dependency)
            records.append(record)
            previous = record.tag
        self.records = tuple(records)
        self.policy = KernelContinuityPolicy(self.crypto, session_id=self.session_id,
                                             task_id=self.task_id, stage_order=self.STAGES)
        self.seal = self.policy.seal(self.records)
        self.final_tag = HypersynthIntegrityVerifier.final_tag(
            self.crypto, session_id=self.session_id, task_id=self.task_id,
            risk_class=self.risk, requirements=self.requirements, stage_order=self.STAGES,
            stage_tags=tuple(item.tag for item in self.attestations),
            continuity_tags=tuple(item.tag for item in self.records), continuity_seal=self.seal.seal,
        )

    def _verify(self, *, attestations=None, seal=None, final_tag=None, session_id=None, task_id=None):
        sid = self.session_id if session_id is None else session_id
        tid = self.task_id if task_id is None else task_id
        context = self.context_tag if session_id is None else self.crypto.digest("hypersynth_session", {
            "session_id": sid, "task_id": tid, "risk_class": self.risk,
            "verification_requirements": self.requirements,
        })
        return HypersynthIntegrityVerifier.verify_exported_integrity(
            self.crypto, session_id=sid, task_id=tid, risk_class=self.risk,
            requirements=self.requirements, stage_order=self.STAGES,
            attestations=self.attestations if attestations is None else attestations,
            payloads=self.payloads, continuity_records=self.records,
            continuity_seal=self.seal if seal is None else seal,
            final_continuity_tag=self.final_tag if final_tag is None else final_tag,
            context_tag=context,
        )

    def test_attack91_external_verifier_does_not_depend_on_policy_sealed_state(self):
        fresh = KernelContinuityPolicy(self.crypto, session_id=self.session_id, task_id=self.task_id, stage_order=self.STAGES)
        self.assertTrue(HypersynthIntegrityVerifier.verify_continuity_seal(
            self.crypto, self.seal, self.records, session_id=self.session_id,
            task_id=self.task_id, stage_order=self.STAGES))
        self.assertTrue(fresh.admit(self.records))

    def test_attack92_cross_session_seal_replay_rejected(self):
        self.assertFalse(self._verify(session_id="other-session"))

    def test_attack93_cross_task_seal_replay_rejected(self):
        self.assertFalse(self._verify(task_id="other-task"))

    def test_attack94_stage_tag_substitution_rejected(self):
        forged = list(self.attestations)
        forged[4] = replace(forged[4], tag="0" * 64)
        self.assertFalse(self._verify(attestations=tuple(forged)))

    def test_attack95_every_continuity_seal_field_is_bound(self):
        fields = {"session_id": "other-session", "task_id": "other-task", "sequence": self.seal.sequence + 1,
                  "first_tag": "0" * 64, "final_tag": "0" * 64, "chain_digest": "0" * 64, "seal": "0" * 64}
        for field, value in fields.items():
            with self.subTest(field=field):
                self.assertFalse(self._verify(seal=replace(self.seal, **{field: value})))

    def test_attack96_exported_collections_and_objects_are_immutable(self):
        with self.assertRaises(TypeError):
            self.attestations[0] = self.attestations[0]
        with self.assertRaises(TypeError):
            self.records[0] = self.records[0]
        with self.assertRaises(Exception):
            self.attestations[0].tag = "0" * 64
        with self.assertRaises(Exception):
            self.records[0].tag = "0" * 64

    def test_attack97_domain_separation_prevents_cross_domain_reuse(self):
        payload = {"x": 1, "stage": "planning"}
        self.assertNotEqual(self.crypto.digest("domain-a", payload), self.crypto.digest("domain-b", payload))

    def test_attack98_canonicalization_is_order_stable_but_type_distinct(self):
        self.assertEqual(self.crypto.canonical({"a": 1, "b": 2}), self.crypto.canonical({"b": 2, "a": 1}))
        self.assertNotEqual(self.crypto.canonical({"x": 1}), self.crypto.canonical({"x": "1"}))

    def test_attack99_final_tag_tamper_fails_closed(self):
        self.assertFalse(self._verify(final_tag="0" * 64))
        self.assertFalse(self._verify(final_tag=""))

    def test_attack100_each_stage_attestation_field_tamper_fails_closed(self):
        fields = ("task_id", "stage", "sequence", "risk_class", "verification_requirements",
                  "payload_digest", "previous_tag", "tag")
        replacements = {"task_id": "foreign-task", "stage": "foreign-stage", "sequence": 99,
                        "risk_class": "high", "verification_requirements": ("different",),
                        "payload_digest": "0" * 64, "previous_tag": "0" * 64, "tag": "0" * 64}
        for stage_index in range(len(self.STAGES)):
            for field in fields:
                with self.subTest(stage=stage_index, field=field):
                    forged = list(self.attestations)
                    forged[stage_index] = replace(forged[stage_index], **{field: replacements[field]})
                    self.assertFalse(self._verify(attestations=tuple(forged)))


if __name__ == "__main__":
    unittest.main()
