import unittest
from dataclasses import replace

from core.crypto import CryptoIntegrity
from core.export_acceptance_141_150 import AcceptanceReceipt, ExportAcceptanceController
from core.acceptance_ledger_151_160 import AcceptanceLedger


class AcceptanceLedger161To170Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"l" * 32)
        self.session = "session-ledger"
        self.task = "task-ledger"
        self.risk = "normal"

    def receipt(self, manifest):
        payload = ExportAcceptanceController._receipt_payload(
            nonce=manifest, manifest_tag=manifest,
            session_id=self.session, task_id=self.task, risk_class=self.risk)
        tag = self.crypto.sign(
            ExportAcceptanceController.DOMAIN, payload,
            counter=ExportAcceptanceController.COUNTER, nonce=manifest).tag
        return AcceptanceReceipt(
            ExportAcceptanceController.ALGORITHM, ExportAcceptanceController.VERSION,
            manifest, ExportAcceptanceController.COUNTER, manifest,
            self.session, self.task, self.risk, tag)

    def populated(self):
        ledger = AcceptanceLedger(self.crypto)
        ledger.append(self.receipt("a" * 64))
        ledger.append(self.receipt("b" * 64))
        ledger.seal()
        return ledger

    def test_attack161_sealed_tail_deletion_is_rejected(self):
        ledger = self.populated()
        ledger._records.pop()
        self.assertFalse(ledger.verify())

    def test_attack162_sealed_record_insertion_is_rejected(self):
        ledger = self.populated()
        record = ledger.records[-1]
        ledger._records.append(record)
        self.assertFalse(ledger.verify())

    def test_attack163_sealed_record_reordering_is_rejected(self):
        ledger = self.populated()
        ledger._records.reverse()
        self.assertFalse(ledger.verify())

    def test_attack164_sealed_field_tampering_is_rejected(self):
        ledger = self.populated()
        ledger._records[0] = replace(ledger._records[0], task_id="tampered")
        self.assertFalse(ledger.verify())

    def test_attack165_sealed_root_tampering_is_rejected(self):
        ledger = self.populated()
        ledger._seal_root = "0" * 64
        self.assertFalse(ledger.verify())

    def test_attack166_sealed_length_anchor_tampering_is_rejected(self):
        ledger = self.populated()
        ledger._seal_length = 1
        self.assertFalse(ledger.verify())

    def test_attack167_missing_seal_metadata_fails_closed(self):
        ledger = self.populated()
        ledger._seal_root = None
        self.assertFalse(ledger.verify())

    def test_attack168_seal_flag_rollback_cannot_make_mutated_history_valid(self):
        ledger = self.populated()
        ledger._sealed = False
        ledger._records.pop()
        self.assertFalse(ledger.verify())

    def test_attack169_explicit_snapshot_must_match_sealed_ledger(self):
        ledger = self.populated()
        snapshot = ledger.records[:-1]
        self.assertFalse(ledger.verify(snapshot))

    def test_attack170_valid_sealed_ledger_remains_verifiable(self):
        ledger = self.populated()
        self.assertTrue(ledger.verify())
        self.assertEqual(len(ledger.records), ledger._seal_length)
        self.assertEqual(ledger.seal_root, ledger._seal_root)


if __name__ == "__main__":
    unittest.main()
