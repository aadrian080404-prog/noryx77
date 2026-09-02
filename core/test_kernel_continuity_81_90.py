import unittest

from core.crypto import CryptoIntegrity
from core.kernel_continuity import KernelContinuity, KernelContinuityRecord
from core.kernel_continuity_81_90 import ContinuitySeal, KernelContinuityPolicy


class KernelContinuityPolicyTests(unittest.TestCase):
    def setUp(self):
        crypto = CryptoIntegrity(b"k" * 32)
        self.records = []
        previous = ""
        for sequence, stage in enumerate(("context", "planning", "hypothesis"), start=1):
            body = crypto.digest("kernel_continuity_test", {
                "stage": stage, "sequence": sequence, "previous": previous
            })
            record = KernelContinuityRecord("task-1", stage, sequence, "s" * 64, "i" * 64,
                                            "o" * 64, "d" * 64, previous, body)
            self.records.append(record)
            previous = body
        self.records = tuple(self.records)
        self.policy = KernelContinuityPolicy(crypto, session_id="session-1", task_id="task-1",
                                             stage_order=("context", "planning", "hypothesis"))

    def test_attack81_exact_stage_order_is_required(self):
        self.assertTrue(self.policy.admit(self.records))
        swapped = (self.records[1], self.records[0], self.records[2])
        self.assertFalse(self.policy.admit(swapped))

    def test_attack82_sequence_rollback_rejected(self):
        forged = list(self.records)
        forged[1] = KernelContinuityRecord(
            forged[1].task_id, forged[1].stage, 1, forged[1].state_digest,
            forged[1].input_digest, forged[1].output_digest, forged[1].dependency_tag,
            forged[1].previous_tag, forged[1].tag,
        )
        self.assertFalse(self.policy.admit(tuple(forged)))

    def test_attack83_task_substitution_rejected(self):
        forged = list(self.records)
        forged[1] = KernelContinuityRecord(
            "other-task", forged[1].stage, forged[1].sequence, forged[1].state_digest,
            forged[1].input_digest, forged[1].output_digest, forged[1].dependency_tag,
            forged[1].previous_tag, forged[1].tag,
        )
        self.assertFalse(self.policy.admit(tuple(forged)))

    def test_attack84_previous_tag_fork_rejected(self):
        forged = list(self.records)
        forged[1] = KernelContinuityRecord(
            forged[1].task_id, forged[1].stage, forged[1].sequence, forged[1].state_digest,
            forged[1].input_digest, forged[1].output_digest, forged[1].dependency_tag,
            "f" * 64, forged[1].tag,
        )
        self.assertFalse(self.policy.admit(tuple(forged)))

    def test_attack85_duplicate_tag_rejected_by_seal_material(self):
        duplicate = list(self.records)
        duplicate[2] = KernelContinuityRecord(
            duplicate[2].task_id, duplicate[2].stage, duplicate[2].sequence,
            duplicate[2].state_digest, duplicate[2].input_digest, duplicate[2].output_digest,
            duplicate[2].dependency_tag, duplicate[2].previous_tag, duplicate[1].tag,
        )
        self.assertFalse(self.policy.admit(tuple(duplicate)))

    def test_attack86_seal_binds_session(self):
        seal = self.policy.seal(self.records)
        forged = ContinuitySeal("other-session", seal.task_id, seal.sequence, seal.first_tag,
                                seal.final_tag, seal.chain_digest, seal.seal)
        self.assertFalse(self.policy.verify_seal(forged, self.records))

    def test_attack87_seal_binds_chain_digest(self):
        policy = KernelContinuityPolicy(self.policy.crypto, session_id="session-2", task_id="task-1",
                                        stage_order=self.policy.stage_order)
        seal = policy.seal(self.records)
        forged = ContinuitySeal(seal.session_id, seal.task_id, seal.sequence, seal.first_tag,
                                seal.final_tag, "0" * 64, seal.seal)
        self.assertFalse(policy.verify_seal(forged, self.records))

    def test_attack88_final_tag_substitution_rejected(self):
        policy = KernelContinuityPolicy(self.policy.crypto, session_id="session-3", task_id="task-1",
                                        stage_order=self.policy.stage_order)
        seal = policy.seal(self.records)
        forged = ContinuitySeal(seal.session_id, seal.task_id, seal.sequence, seal.first_tag,
                                "0" * 64, seal.chain_digest, seal.seal)
        self.assertFalse(policy.verify_seal(forged, self.records))

    def test_attack89_sealed_policy_rejects_second_seal(self):
        policy = KernelContinuityPolicy(self.policy.crypto, session_id="session-4", task_id="task-1",
                                        stage_order=self.policy.stage_order)
        policy.seal(self.records)
        with self.assertRaises(ValueError):
            policy.seal(self.records)

    def test_attack90_malformed_record_fails_closed(self):
        self.assertFalse(self.policy.admit((object(),)))
        self.assertFalse(self.policy.verify_seal(object(), self.records))


if __name__ == "__main__":
    unittest.main()
