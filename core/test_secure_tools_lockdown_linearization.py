import threading
import unittest

from .contracts import ActionSpec
from .crypto import CryptoIntegrity
from .secure_tools import SecureToolExecutor
from .security_lockdown import SecurityLockdown
from .verification import VerificationEngine


class PermissivePolicy:
    def allows(self, action):
        return True


class SecureToolLockdownLinearizationTests(unittest.TestCase):
    def _lockdown(self):
        return SecurityLockdown(CryptoIntegrity(), lambda proof: True)

    def test_incident_between_initial_check_and_final_execution_is_not_bypassed(self):
        lockdown = self._lockdown()
        verifier = VerificationEngine()
        executor = SecureToolExecutor(PermissivePolicy(), verifier, CryptoIntegrity(), lockdown=lockdown)
        calls = []
        inspected = threading.Event()
        release = threading.Event()

        def handler(target, params):
            calls.append(True)
            return "must-not-run"

        executor.capabilities.register("compute", handler)

        class BlockingSecurity:
            def inspect(self, action):
                inspected.set()
                release.wait(timeout=2)
                return type("Decision", (), {"allowed": True, "reason": "allowed", "risk_class": action.risk_class})()

        executor.security = BlockingSecurity()
        action = ActionSpec("lockdown-race", "compute")
        result = {}

        def run():
            result["value"] = executor.execute(action)

        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(inspected.wait(timeout=2))
        lockdown.record_incident("concurrent_attack", severity=10)
        release.set()
        worker.join(timeout=2)

        output, check = result["value"]
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "global_lockdown")
        self.assertEqual(calls, [])

    def test_lockdown_transition_waits_for_handler_inside_execution_guard(self):
        lockdown = self._lockdown()
        verifier = VerificationEngine()
        executor = SecureToolExecutor(PermissivePolicy(), verifier, CryptoIntegrity(), lockdown=lockdown)
        entered = threading.Event()
        release = threading.Event()
        incident_done = threading.Event()
        calls = []

        def handler(target, params):
            entered.set()
            release.wait(timeout=2)
            calls.append(True)
            return "ok"

        executor.capabilities.register("compute", handler)

        def raise_incident():
            lockdown.record_incident("concurrent_attack", severity=10)
            incident_done.set()

        incident_thread = threading.Thread(target=raise_incident)
        result = {}

        def run():
            result["value"] = executor.execute(ActionSpec("linearized", "compute"))

        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(entered.wait(timeout=2))
        incident_thread.start()
        self.assertFalse(incident_done.wait(timeout=0.1))
        release.set()
        worker.join(timeout=2)
        incident_thread.join(timeout=2)

        output, check = result["value"]
        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)
        self.assertEqual(calls, [True])
        self.assertTrue(incident_done.is_set())
        self.assertFalse(lockdown.permits())


if __name__ == "__main__":
    unittest.main()
