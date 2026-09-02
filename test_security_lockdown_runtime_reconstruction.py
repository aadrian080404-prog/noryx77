import copy
import unittest

from core.crypto import CryptoIntegrity
from core.hypersynth_runtime import HypersynthRuntime
from core.security_lockdown import SecurityLockdown


KEY = b"K" * 32


class SecurityLockdownRuntimeReconstructionTests(unittest.TestCase):
    def test_reconstructed_runtime_inherits_lockdown_from_authenticated_seal(self):
        first = HypersynthRuntime(crypto=CryptoIntegrity(KEY), admin_authorizer=lambda proof: True)
        first.security_lockdown.record_incident("runtime_reconstruction_attack", severity=10)
        self.assertEqual(first.security_lockdown.state.mode, SecurityLockdown.EMERGENCY)

        seal = first.export_lockdown_seal()
        second = HypersynthRuntime(
            crypto=CryptoIntegrity(KEY),
            admin_authorizer=lambda proof: True,
            lockdown_seal=seal,
        )

        self.assertEqual(second.security_lockdown.state, first.security_lockdown.state)
        self.assertFalse(second.security_lockdown.permits())
        self.assertIs(second.action_gate.lockdown, second.security_lockdown)

    def test_reconstruction_rejects_tampered_lockdown_seal(self):
        first = HypersynthRuntime(crypto=CryptoIntegrity(KEY))
        first.security_lockdown.record_incident("tamper", severity=10)
        seal = first.export_lockdown_seal()
        tampered = copy.deepcopy(seal)
        tampered["payload"] = bytes(seal["payload"][:-1]) + bytes([seal["payload"][-1] ^ 1])

        with self.assertRaisesRegex(ValueError, "invalid_lockdown_continuity_seal"):
            HypersynthRuntime(crypto=CryptoIntegrity(KEY), lockdown_seal=tampered)

    def test_stale_normal_seal_cannot_clear_new_lockdown(self):
        crypto = CryptoIntegrity(KEY)
        lockdown = SecurityLockdown(crypto, lambda proof: True)
        normal_seal = lockdown.export_seal()
        lockdown.record_incident("new_incident", severity=10)

        with self.assertRaisesRegex(ValueError, "stale_lockdown_seal"):
            lockdown.restore_seal(normal_seal)
        self.assertFalse(lockdown.permits())

    def test_new_crypto_key_cannot_reconstruct_lockdown_from_old_seal(self):
        first = HypersynthRuntime(crypto=CryptoIntegrity(KEY))
        first.security_lockdown.record_incident("key_boundary", severity=10)
        seal = first.export_lockdown_seal()

        with self.assertRaisesRegex(ValueError, "invalid_lockdown_continuity_seal"):
            HypersynthRuntime(crypto=CryptoIntegrity(b"Z" * 32), lockdown_seal=seal)


if __name__ == "__main__":
    unittest.main()
