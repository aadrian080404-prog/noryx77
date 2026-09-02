import unittest
from concurrent.futures import ThreadPoolExecutor

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


class ActionGateConcurrencyTests(unittest.TestCase):
    def test_concurrent_authorization_preserves_unique_crypto_counters(self):
        crypto = CryptoIntegrity()
        gate = ActionGate(
            PermissivePolicy(),
            PermissiveSecurity(),
            RuntimeLimits(max_actions_per_task=256),
            crypto=crypto,
        )
        actions = [ActionSpec(f"action-{index}", "compute", target=str(index)) for index in range(128)]

        with ThreadPoolExecutor(max_workers=16) as pool:
            decisions = list(pool.map(gate.authorize, actions))

        self.assertTrue(all(decision.allowed for decision in decisions))
        self.assertTrue(all(decision.verification.valid for decision in decisions))
        self.assertEqual(gate._authorization_counter, len(actions))
        self.assertEqual(crypto._highest.get("action_gate"), len(actions) - 1)
        self.assertEqual(len(crypto._nonces.get("action_gate", set())), len(actions))

    def test_concurrent_authorization_does_not_create_replay_collisions(self):
        crypto = CryptoIntegrity()
        gate = ActionGate(
            PermissivePolicy(),
            PermissiveSecurity(),
            RuntimeLimits(max_actions_per_task=512),
            crypto=crypto,
        )
        actions = [ActionSpec(f"action-{index}", "compute") for index in range(256)]

        with ThreadPoolExecutor(max_workers=32) as pool:
            decisions = list(pool.map(gate.authorize, actions))

        self.assertEqual(sum(decision.allowed for decision in decisions), len(actions))
        self.assertEqual(gate._authorization_counter, len(actions))
        self.assertEqual(len(crypto._nonces["action_gate"]), len(actions))


if __name__ == "__main__":
    unittest.main()
