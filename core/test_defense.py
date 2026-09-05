import unittest

from .defense import (
    AccessRequest,
    DefenseController,
    DefenseMode,
    ImmutableCoreManifest,
    OfflineArtifact,
    OfflineRecoveryCatalog,
    SegmentationPolicy,
    SecurityEvent,
    TrustDecision,
)


class DefenseInfrastructureTests(unittest.TestCase):
    def request(self, component="agent", capability="observe", target=""):
        return AccessRequest("principal", component, capability, target, "session")

    def test_deny_by_default_segmentation(self):
        policy = SegmentationPolicy()
        controller = DefenseController(segmentation=policy)
        self.assertEqual(controller.authorize(self.request(target="memory")).decision, TrustDecision.DENY)
        policy.allow("agent", "memory")
        self.assertEqual(controller.authorize(self.request(target="memory")).decision, TrustDecision.ALLOW)
        policy.revoke("agent", "memory")
        self.assertEqual(controller.authorize(self.request(target="memory")).decision, TrustDecision.DENY)

    def test_revocation_survives_other_state_changes(self):
        controller = DefenseController()
        controller.revoke("principal")
        controller.trust_component("agent")
        self.assertEqual(controller.authorize(self.request()).reason, "principal_revoked")

    def test_lockdown_is_fail_closed(self):
        controller = DefenseController()
        controller.enter_lockdown("anomaly")
        decision = controller.authorize(self.request())
        self.assertEqual(controller.mode, DefenseMode.LOCKDOWN)
        self.assertEqual(decision.decision, TrustDecision.DENY)
        with self.assertRaises(PermissionError):
            controller.trust_component("new")

    def test_recovery_requires_verified_trusted_components(self):
        controller = DefenseController()
        controller.trust_component("core")
        controller.enter_lockdown("incident")
        controller.enter_recovery()
        with self.assertRaises(PermissionError):
            controller.finish_recovery(verified_components=("untrusted",))
        controller.finish_recovery(verified_components=("core",))
        self.assertEqual(controller.mode, DefenseMode.RESTRICTED)
        controller.resume_normal()
        self.assertEqual(controller.mode, DefenseMode.NORMAL)

    def test_isolated_component_cannot_be_authorized(self):
        controller = DefenseController()
        controller.isolate("agent")
        decision = controller.authorize(self.request())
        self.assertEqual(decision.decision, TrustDecision.ISOLATE)
        self.assertEqual(decision.reason, "component_isolated")

    def test_restricted_mode_only_allows_recovery_observation_verification(self):
        controller = DefenseController()
        controller.trust_component("core")
        controller.enter_lockdown("incident")
        controller.enter_recovery()
        controller.finish_recovery(verified_components=("core",))
        self.assertEqual(controller.authorize(self.request(capability="observe")).decision, TrustDecision.ALLOW)
        self.assertEqual(controller.authorize(self.request(capability="execute")).decision, TrustDecision.DENY)

    def test_event_validation_and_capacity(self):
        controller = DefenseController()
        event = SecurityEvent("e1", "anomaly", "agent", 0.9, "test")
        controller.record_event(event)
        self.assertEqual(controller.events(), (event,))
        with self.assertRaises(ValueError):
            SecurityEvent("e2", "anomaly", "agent", 1.1)

    def test_immutable_manifest_is_exact(self):
        digest = "a" * 64
        manifest = ImmutableCoreManifest({"identity": digest, "policy": "b" * 64})
        self.assertTrue(manifest.verify({"identity": digest, "policy": "b" * 64}))
        self.assertFalse(manifest.verify({"identity": digest, "policy": "c" * 64}))

    def test_offline_catalog_requires_exact_encrypted_artifact(self):
        catalog = OfflineRecoveryCatalog()
        artifact = OfflineArtifact("backup-1", "1", "a" * 64, True)
        catalog.register(artifact)
        self.assertTrue(catalog.verify("backup-1", "a" * 64))
        self.assertFalse(catalog.verify("backup-1", "b" * 64))
        self.assertFalse(catalog.verify("missing", "a" * 64))


if __name__ == "__main__":
    unittest.main()
