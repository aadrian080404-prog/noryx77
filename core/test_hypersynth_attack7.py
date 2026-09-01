import unittest

from .audit import AuditLog


class Attack7Tests(unittest.TestCase):
    def test_audit_record_rejects_empty_event(self):
        audit = AuditLog()
        with self.assertRaises(ValueError):
            audit.record("")

    def test_audit_record_does_not_retain_mutable_input_alias(self):
        audit = AuditLog()
        payload = {"nested": ["original"]}
        audit.record("test", payload=payload)
        payload["nested"].append("forged")
        self.assertEqual(audit.snapshot()[0]["payload"], {"nested": ["original"]})

    def test_audit_snapshot_isolation_prevents_evidence_poisoning(self):
        audit = AuditLog()
        audit.record("test", payload={"nested": ["original"]})
        snapshot = audit.snapshot()
        snapshot[0]["payload"]["nested"].append("forged")
        self.assertEqual(audit.snapshot()[0]["payload"], {"nested": ["original"]})

    def test_audit_record_return_value_is_isolated(self):
        audit = AuditLog()
        entry = audit.record("test", payload={"nested": ["original"]})
        entry["payload"]["nested"].append("forged")
        self.assertEqual(audit.snapshot()[0]["payload"], {"nested": ["original"]})


if __name__ == "__main__":
    unittest.main()
