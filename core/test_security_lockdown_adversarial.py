import threading
import unittest

from .crypto import CryptoIntegrity
from .security_lockdown import SecurityLockdown


class SecurityLockdownAdversarialTests(unittest.TestCase):
    def test_reentrant_admin_authorizer_cannot_deadlock_lockdown(self):
        crypto = CryptoIntegrity()
        holder = {}

        def authorizer(proof):
            holder["lockdown"].record_incident("reentrant_authorizer", severity=1)
            return True

        lockdown = SecurityLockdown(crypto, authorizer)
        holder["lockdown"] = lockdown
        lockdown.record_incident("integrity_failure", severity=10)
        challenge = lockdown.admin_challenge()
        with self.assertRaises(PermissionError):
            lockdown.recover(challenge)
        self.assertEqual(lockdown.state.mode, SecurityLockdown.EMERGENCY)
        self.assertEqual(lockdown.state.incidents, 2)

    def test_concurrent_recovery_has_single_winner(self):
        crypto = CryptoIntegrity()
        entered = threading.Event()
        release = threading.Event()

        def authorizer(proof):
            entered.set()
            release.wait(timeout=2)
            return True

        lockdown = SecurityLockdown(crypto, authorizer)
        lockdown.record_incident("integrity_failure", severity=10)
        challenge = lockdown.admin_challenge()
        results = []

        def recover():
            try:
                results.append(("ok", lockdown.recover(challenge)))
            except PermissionError:
                results.append(("denied", None))

        first = threading.Thread(target=recover)
        second = threading.Thread(target=recover)
        first.start()
        self.assertTrue(entered.wait(timeout=2))
        second.start()
        release.set()
        first.join(timeout=2)
        second.join(timeout=2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual([item[0] for item in results].count("ok"), 1)
        self.assertEqual([item[0] for item in results].count("denied"), 1)
        self.assertEqual(lockdown.state.mode, SecurityLockdown.NORMAL)

    def test_recovery_is_invalidated_when_generation_changes_during_authorization(self):
        crypto = CryptoIntegrity()
        entered = threading.Event()
        release = threading.Event()
        holder = {}

        def authorizer(proof):
            entered.set()
            release.wait(timeout=2)
            return True

        lockdown = SecurityLockdown(crypto, authorizer)
        holder["lockdown"] = lockdown
        lockdown.record_incident("integrity_failure", severity=10)
        challenge = lockdown.admin_challenge()
        result = []

        def recover():
            try:
                lockdown.recover(challenge)
                result.append("ok")
            except PermissionError:
                result.append("denied")

        thread = threading.Thread(target=recover)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        lockdown.record_incident("race", severity=1)
        release.set()
        thread.join(timeout=2)
        self.assertEqual(result, ["denied"])
        self.assertNotEqual(lockdown.state.mode, SecurityLockdown.NORMAL)


if __name__ == "__main__":
    unittest.main()
