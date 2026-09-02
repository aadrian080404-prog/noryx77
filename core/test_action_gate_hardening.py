import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from .actions import ActionGate
from .contracts import ActionSpec
from .crypto import CryptoIntegrity
from .limits import RuntimeLimits


class PermissivePolicy:
    def allows(self, action):
        return True


class PermissiveSecurity:
    def allows(self, action):
        return True


class ActionGateHardeningTests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity()
        self.policy = PermissivePolicy()
        self.security = PermissiveSecurity()
        self.limits = RuntimeLimits(max_actions_per_task=256, max_tool_calls_per_task=256)

    def test_authorization_envelope_binds_exact_action(self):
        gate = ActionGate(self.policy, self.security, self.limits, crypto=self.crypto)
        action = ActionSpec("a", "read", target="resource-a", parameters={"scope": "read"})
        envelope = self.crypto.sign("action_gate", {"action": "a", "action_type": "read", "target": "resource-a", "parameters": {"scope": "read"}, "risk_class": "normal", "requires_authorization": False}, 0)
        forged = replace(envelope, payload=self.crypto.canonical({"action": "a", "action_type": "write", "target": "resource-a", "parameters": {"scope": "write"}, "risk_class": "normal", "requires_authorization": False}))
        self.assertFalse(self.crypto.verify(forged))
        decision = gate.authorize(action)
        self.assertTrue(decision.allowed)

    def test_authorization_counter_is_not_reused_after_failed_verification(self):
        class FailingCrypto(CryptoIntegrity):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def verify(self, envelope, *, consume=True):
                self.calls += 1
                return False if self.calls == 1 else super().verify(envelope, consume=consume)

        crypto = FailingCrypto()
        gate = ActionGate(self.policy, self.security, self.limits, crypto=crypto)
        first = gate.authorize(ActionSpec("a", "read"))
        second = gate.authorize(ActionSpec("b", "read"))
        self.assertFalse(first.allowed)
        self.assertEqual(first.verification.reason, "authorization_integrity_failure")
        self.assertTrue(second.allowed)
        self.assertEqual(gate._authorization_counter, 2)

    def test_non_canonical_parameters_fail_closed(self):
        gate = ActionGate(self.policy, self.security, self.limits, crypto=self.crypto)
        action = ActionSpec("bad", "read", parameters={"value": float("nan")})
        decision = gate.authorize(action)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "authorization_integrity_failure")

    def test_action_gate_rejects_bool_counts(self):
        gate = ActionGate(self.policy, self.security, self.limits, crypto=self.crypto)
        decision = gate.authorize(ActionSpec("a", "read"), calls_used=True)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_call_count")

    def test_concurrent_authorizations_have_unique_counters(self):
        gate = ActionGate(self.policy, self.security, self.limits, crypto=self.crypto)
        actions = [ActionSpec(f"a-{i}", "read", target=str(i)) for i in range(128)]
        with ThreadPoolExecutor(max_workers=16) as pool:
            decisions = list(pool.map(gate.authorize, actions))
        self.assertTrue(all(d.allowed for d in decisions))
        self.assertEqual(gate._authorization_counter, 128)
        self.assertEqual(len(self.crypto._nonces.get("action_gate", set())), 128)


if __name__ == "__main__":
    unittest.main()
