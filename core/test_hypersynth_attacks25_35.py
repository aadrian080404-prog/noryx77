import unittest

from .actions import ActionGate
from .contracts import ActionSpec
from .crypto import CryptoEnvelope, CryptoIntegrity
from .limits import RuntimeLimits
from .memory import MemoryItem, MemoryStore


class AllowAll:
    def allows(self, action):
        return True


class Attack25To35Tests(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoIntegrity(b"k" * 32)

    # Attack 25: memory tampering
    def test_memory_tampering_is_detected(self):
        store = MemoryStore(crypto=self.crypto)
        store.put(MemoryItem("m25", {"value": 1}))
        store._items["m25"] = MemoryItem("m25", {"value": 999})
        with self.assertRaisesRegex(MemoryError, "memory_integrity_failure"):
            store.get("m25")

    # Attack 26: action authorization authentication
    def test_action_gate_cryptographically_binds_authorization_input(self):
        security = AllowAll()
        gate = ActionGate(security, security, RuntimeLimits(), crypto=self.crypto)
        action = ActionSpec("a26", "compute")
        decision = gate.authorize(action)
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.verification.valid)

    # Attack 27: domain separation
    def test_domain_separation_prevents_cross_domain_digest_reuse(self):
        payload = {"task_id": "t27", "value": "x"}
        digest = self.crypto.digest("task", payload)
        self.assertFalse(self.crypto.verify_digest("action", payload, digest))
        self.assertTrue(self.crypto.verify_digest("task", payload, digest))

    # Attack 28: payload forgery
    def test_payload_forgery_invalidates_digest(self):
        payload = {"task_id": "t28", "risk": "normal"}
        digest = self.crypto.digest("task", payload)
        forged = {"task_id": "t28", "risk": "high"}
        self.assertFalse(self.crypto.verify_digest("task", forged, digest))

    # Attack 29: nonce replay
    def test_nonce_replay_is_rejected(self):
        envelope = self.crypto.sign("execution", {"task": "t29"}, 0, nonce="fixed")
        self.assertTrue(self.crypto.verify(envelope))
        self.assertFalse(self.crypto.verify(envelope))

    # Attack 30: counter rollback
    def test_counter_rollback_is_rejected(self):
        first = self.crypto.sign("execution", {"task": "t30"}, 2, nonce="n2")
        old = self.crypto.sign("execution", {"task": "t30"}, 1, nonce="n1")
        self.assertTrue(self.crypto.verify(first))
        self.assertFalse(self.crypto.verify(old))

    # Attack 31: counter is scoped by domain
    def test_counter_state_is_domain_scoped(self):
        first = self.crypto.sign("task", {"v": 1}, 1, nonce="task1")
        second = self.crypto.sign("action", {"v": 1}, 1, nonce="action1")
        self.assertTrue(self.crypto.verify(first))
        self.assertTrue(self.crypto.verify(second))

    # Attack 32: malformed cryptographic envelope
    def test_malformed_envelope_fails_closed(self):
        malformed = CryptoEnvelope("task", "nonce", 0, b"payload", "bad")
        self.assertFalse(self.crypto.verify(malformed))
        self.assertFalse(self.crypto.verify(object()))

    # Attack 33: canonical serialization stability
    def test_canonical_serialization_is_order_independent(self):
        left = {"a": 1, "b": {"x": 2, "y": 3}}
        right = {"b": {"y": 3, "x": 2}, "a": 1}
        self.assertEqual(self.crypto.canonical(left), self.crypto.canonical(right))
        self.assertEqual(self.crypto.digest("canonical", left), self.crypto.digest("canonical", right))

    # Attack 34: key separation
    def test_different_master_keys_cannot_verify_each_other(self):
        envelope = self.crypto.sign("task", {"id": "t34"}, 0, nonce="n34")
        other = CryptoIntegrity(b"x" * 32)
        self.assertFalse(other.verify(envelope))

    # Attack 35: final authenticated multi-domain evidence
    def test_final_attestation_requires_valid_chain_and_domain_binding(self):
        task = {"task_id": "t35", "risk": "normal"}
        result = {"task_id": "t35:0", "status": "completed"}
        task_tag = self.crypto.digest("task", task)
        result_tag = self.crypto.digest("result", result)
        self.assertTrue(self.crypto.verify_digest("task", task, task_tag))
        self.assertTrue(self.crypto.verify_digest("result", result, result_tag))
        self.assertFalse(self.crypto.verify_digest("task", result, result_tag))


if __name__ == "__main__":
    unittest.main()
