import unittest

from .audit import AuditLog


class Attack24Tests(unittest.TestCase):
    def test_audit_chain_authenticates_events(self):
        audit = AuditLog(b"k" * 32)
        audit.record("start", task_id="t24")
        audit.record("finish", status="ok")
        self.assertTrue(audit.verify())

    def test_tampered_event_is_rejected(self):
        audit = AuditLog(b"k" * 32)
        audit.record("start", task_id="t24")
        events = list(audit.snapshot())
        events[0]["task_id"] = "forged"
        self.assertFalse(audit.verify(events))

    def test_removed_or_reordered_event_is_rejected(self):
        audit = AuditLog(b"k" * 32)
        audit.record("a")
        audit.record("b")
        events = list(audit.snapshot())
        self.assertFalse(audit.verify(events[1:]))
        self.assertFalse(audit.verify(tuple(reversed(events))))

    def test_wrong_key_is_rejected(self):
        audit = AuditLog(b"k" * 32)
        audit.record("start")
        forged_verifier = AuditLog(b"x" * 32)
        self.assertFalse(forged_verifier.verify(audit.snapshot()))

    def test_short_key_is_rejected(self):
        with self.assertRaises(ValueError):
            AuditLog(b"short")


if __name__ == "__main__":
    unittest.main()
