import unittest

from .actions import ActionGate
from .contracts import ActionSpec
from .crypto import CryptoIntegrity
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .secure_tools import SecureToolExecutor
from .security_lockdown import SecurityLockdown
from .verification import VerificationEngine


class PermissivePolicy:
    def allows(self, action):
        return True

    def evaluate(self, action):
        return {"allowed": True, "reason": "allowed"}


class PermissiveSecurity:
    def allows(self, action):
        return True


class LockdownIntegrationTests(unittest.TestCase):
    def test_runtime_rejects_before_task_processing_when_locked(self):
        runtime = HypersynthRuntime()
        runtime.security_lockdown.record_incident("integrity_failure", severity=10)
        result = runtime.run(object())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "global_lockdown")

    def test_action_gate_rejects_while_locked(self):
        crypto = CryptoIntegrity()
        lockdown = SecurityLockdown(crypto, lambda proof: proof == b"admin")
        lockdown.record_incident("integrity_failure", severity=10)
        gate = ActionGate(PermissivePolicy(), PermissiveSecurity(), RuntimeLimits(max_actions_per_task=8, max_tool_calls_per_task=8), crypto=crypto, lockdown=lockdown)
        decision = gate.authorize(ActionSpec("blocked", "read"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "global_lockdown")

    def test_tool_executor_rejects_while_locked(self):
        crypto = CryptoIntegrity()
        lockdown = SecurityLockdown(crypto, lambda proof: proof == b"admin")
        lockdown.record_incident("integrity_failure", severity=10)
        executor = SecureToolExecutor(PermissivePolicy(), VerificationEngine(), crypto, lockdown=lockdown)
        executor.capabilities.register("compute", lambda target, params: "must-not-run")
        output, check = executor.execute(ActionSpec("blocked", "compute"))
        self.assertIsNone(output)
        self.assertEqual(check.reason, "global_lockdown")

    def test_only_external_admin_authority_can_clear_lockdown(self):
        authorizer_calls = []
        def authorizer(proof):
            authorizer_calls.append(proof)
            return proof == expected_challenge
        crypto = CryptoIntegrity()
        lockdown = SecurityLockdown(crypto, authorizer)
        lockdown.record_incident("integrity_failure", severity=10)
        with self.assertRaises(PermissionError):
            lockdown.recover(b"attacker")
        expected_challenge = lockdown.admin_challenge()
        state = lockdown.recover(expected_challenge)
        self.assertEqual(state.mode, SecurityLockdown.NORMAL)
        self.assertTrue(lockdown.permits())
        self.assertEqual(authorizer_calls, [expected_challenge])


if __name__ == "__main__":
    unittest.main()
