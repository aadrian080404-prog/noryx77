import unittest

from .crypto import CryptoIntegrity
from .security_lockdown import SecurityLockdown


class SecurityLockdownTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity()
        self.lockdown = SecurityLockdown(
            self.crypto,
            lambda proof: proof == b"admin-proof",
            restricted_threshold=3,
            lockdown_threshold=5,
            emergency_threshold=8,
        )

    def test_repeated_incidents_escalate_and_deny_non_admin(self):
        self.assertTrue(self.lockdown.permits())
        self.lockdown.record_incident("auth_failure", severity=2)
        self.assertEqual(self.lockdown.state.mode, SecurityLockdown.NORMAL)
        self.lockdown.record_incident("replay", severity=2)
        self.assertEqual(self.lockdown.state.mode, SecurityLockdown.RESTRICTED)
        self.lockdown.record_incident("tamper", severity=1)
        self.assertEqual(self.lockdown.state.mode, SecurityLockdown.LOCKDOWN)
        self.assertFalse(self.lockdown.permits())
        self.assertTrue(self.lockdown.permits(is_admin=True))

    def test_critical_incident_enters_emergency_mode(self):
        state = self.lockdown.record_incident("integrity_failure", severity=10)
        self.assertEqual(state.mode, SecurityLockdown.EMERGENCY)
        self.assertFalse(self.lockdown.permits())

    def test_invalid_admin_cannot_recover(self):
        self.lockdown.record_incident("tamper", severity=5)
        with self.assertRaises(PermissionError):
            self.lockdown.recover(b"attacker")
        self.assertEqual(self.lockdown.state.mode, SecurityLockdown.LOCKDOWN)

    def test_external_admin_authority_is_required_for_recovery(self):
        self.lockdown.record_incident("tamper", severity=5)
        state = self.lockdown.recover(b"admin-proof")
        self.assertEqual(state.mode, SecurityLockdown.NORMAL)
        self.assertTrue(self.lockdown.permits())

    def test_lockdown_seal_detects_tampering(self):
        self.lockdown.record_incident("tamper", severity=5)
        seal = self.lockdown.export_seal()
        forged = dict(seal)
        forged["payload"] = forged["payload"].replace(b"lockdown", b"normal", 1)
        with self.assertRaises(ValueError):
            self.lockdown.restore_seal(forged)

    def test_stale_seal_cannot_rollback_state(self):
        self.lockdown.record_incident("tamper", severity=5)
        seal = self.lockdown.export_seal()
        self.lockdown.recover(b"admin-proof")
        self.lockdown.record_incident("critical", severity=10)
        with self.assertRaises(ValueError):
            self.lockdown.restore_seal(seal)
        self.assertEqual(self.lockdown.state.mode, SecurityLockdown.EMERGENCY)

    def test_bool_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.lockdown.record_incident("bad", severity=True)


if __name__ == "__main__":
    unittest.main()
