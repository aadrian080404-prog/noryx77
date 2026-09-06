import unittest
from hashlib import sha256

from .global_fabric import (
    GlobalIdentityAuthorizationFabric,
    GlobalMemoryFabric,
    IdentityAuthorization,
    MemoryLevel,
)


class GlobalFabricTests(unittest.TestCase):
    def setUp(self):
        self.policy_digest = "a" * 64
        self.authorization_digest = "b" * 64

    def authorization(self, identity="identity-1", session="session-1", device="device-1"):
        return IdentityAuthorization(
            identity,
            session,
            device,
            "user",
            ("search",),
            self.policy_digest,
            self.authorization_digest,
        )

    def test_session_binding_rejects_identity_swap(self):
        fabric = GlobalIdentityAuthorizationFabric()
        fabric.bind(self.authorization())
        with self.assertRaises(PermissionError):
            fabric.bind(self.authorization(identity="identity-2"))

    def test_session_binding_rejects_device_swap(self):
        fabric = GlobalIdentityAuthorizationFabric()
        fabric.bind(self.authorization())
        with self.assertRaises(PermissionError):
            fabric.bind(self.authorization(device="device-2"))

    def test_authorization_requires_capability_and_policy(self):
        fabric = GlobalIdentityAuthorizationFabric()
        fabric.bind(self.authorization())
        self.assertEqual(fabric.authorize("session-1", "search", self.policy_digest).identity_id, "identity-1")
        with self.assertRaises(PermissionError):
            fabric.authorize("session-1", "publish", self.policy_digest)
        with self.assertRaises(PermissionError):
            fabric.authorize("session-1", "search", "c" * 64)

    def test_revoke_removes_authorization(self):
        fabric = GlobalIdentityAuthorizationFabric()
        fabric.bind(self.authorization())
        fabric.revoke("session-1")
        with self.assertRaises(PermissionError):
            fabric.authorize("session-1", "search", self.policy_digest)

    def test_memory_version_increments_and_digest_changes(self):
        fabric = GlobalMemoryFabric(max_records=2)
        first = fabric.put("record-1", MemoryLevel.L0_DEVICE, b"one", b"prov", ("device-1",))
        second = fabric.put("record-1", MemoryLevel.L1_EDGE, b"two", b"prov", ("edge-1", "edge-2"))
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(second.payload_digest, sha256(b"two").hexdigest())
        self.assertEqual(len(fabric.snapshot()), 1)

    def test_memory_capacity_is_bounded(self):
        fabric = GlobalMemoryFabric(max_records=1)
        fabric.put("record-1", MemoryLevel.L0_DEVICE, b"one", b"prov", ("device-1",))
        with self.assertRaises(MemoryError):
            fabric.put("record-2", MemoryLevel.L0_DEVICE, b"two", b"prov", ("device-2",))

    def test_memory_redundancy_requirement_fails_closed(self):
        fabric = GlobalMemoryFabric()
        fabric.put("record-1", MemoryLevel.L0_DEVICE, b"one", b"prov", ("device-1",))
        with self.assertRaises(RuntimeError):
            fabric.require_redundancy("record-1", minimum_replicas=2)
        fabric.put("record-1", MemoryLevel.L1_EDGE, b"two", b"prov", ("edge-1", "edge-2"))
        self.assertEqual(len(fabric.require_redundancy("record-1", 2).replicas), 2)


if __name__ == "__main__":
    unittest.main()
