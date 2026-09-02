import unittest
from dataclasses import replace

from core.crypto import CryptoIntegrity
from core.export_acceptance_141_150 import AcceptanceReceipt, ExportAcceptanceController
from core.acceptance_ledger_151_160 import AcceptanceLedger, AcceptanceLedgerRecord


class AcceptanceLedger151To160Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"l" * 32)
        self.session = "session-ledger"
        self.task = "task-ledger"
        self.risk = "normal"

    def receipt(self, manifest="a" * 64, session=None, task=None, risk=None):
        session = self.session if session is None else session
        task = self.task if task is None else task
        risk = self.risk if risk is None else risk
        payload = ExportAcceptanceController._receipt_payload(
            nonce=manifest, manifest_tag=manifest, session_id=session,
            task_id=task, risk_class=risk)
        tag = self.crypto.sign(
            ExportAcceptanceController.DOMAIN, payload,
            counter=ExportAcceptanceController.COUNTER, nonce=manifest).tag
        return AcceptanceReceipt(
            ExportAcceptanceController.ALGORITHM, ExportAcceptanceController.VERSION,
            manifest, ExportAcceptanceController.COUNTER, manifest,
            session, task, risk, tag)

    def test_attack151_forged_receipt_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        forged = AcceptanceReceipt("HMAC-SHA256", 1, "b" * 64, 0, "b" * 64,
                                   self.session, self.task, self.risk, "0" * 64)
        with self.assertRaises(ValueError):
            ledger.append(forged)
        self.assertTrue(ledger.verify())

    def test_attack152_wrong_key_receipt_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        other = CryptoIntegrity(b"x" * 32)
        payload = ExportAcceptanceController._receipt_payload(
            nonce="c" * 64, manifest_tag="c" * 64, session_id=self.session,
            task_id=self.task, risk_class=self.risk)
        tag = other.sign(ExportAcceptanceController.DOMAIN, payload, counter=0, nonce="c" * 64).tag
        receipt = AcceptanceReceipt("HMAC-SHA256", 1, "c" * 64, 0, "c" * 64,
                                    self.session, self.task, self.risk, tag)
        with self.assertRaises(ValueError):
            ledger.append(receipt)

    def test_attack153_duplicate_manifest_admission_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        ledger.append(self.receipt())
        with self.assertRaises(ValueError):
            ledger.append(self.receipt())
        self.assertTrue(ledger.verify())

    def test_attack154_record_tag_tampering_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        record = ledger.append(self.receipt())
        forged = replace(record, tag="0" * 64)
        self.assertFalse(ledger.verify((forged,)))

    def test_attack155_record_identity_tampering_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        record = ledger.append(self.receipt())
        forged = replace(record, task_id="foreign-task")
        self.assertFalse(ledger.verify((forged,)))

    def test_attack156_record_order_swap_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        first = ledger.append(self.receipt("a" * 64))
        second = ledger.append(self.receipt("b" * 64))
        self.assertFalse(ledger.verify((second, first)))

    def test_attack157_record_deletion_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        first = ledger.append(self.receipt("a" * 64))
        ledger.append(self.receipt("b" * 64))
        self.assertFalse(ledger.verify((first,)))

    def test_attack158_record_duplication_is_rejected(self):
        ledger = AcceptanceLedger(self.crypto)
        first = ledger.append(self.receipt())
        self.assertFalse(ledger.verify((first, first)))

    def test_attack159_sealed_ledger_rejects_late_append_and_second_seal(self):
        ledger = AcceptanceLedger(self.crypto)
        ledger.append(self.receipt())
        ledger.seal()
        with self.assertRaises(RuntimeError):
            ledger.append(self.receipt("b" * 64))
        with self.assertRaises(RuntimeError):
            ledger.seal()

    def test_attack160_empty_or_malformed_export_history_fails_closed(self):
        ledger = AcceptanceLedger(self.crypto)
        self.assertTrue(ledger.verify(()))
        malformed = AcceptanceLedgerRecord(1, "a" * 64, "b" * 64,
                                           self.session, self.task, self.risk, "", "0" * 64)
        self.assertFalse(ledger.verify((malformed,)))


if __name__ == "__main__":
    unittest.main()
