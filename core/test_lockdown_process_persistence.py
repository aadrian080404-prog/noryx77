import tempfile
import unittest
from pathlib import Path

from core.crypto import CryptoIntegrity
from core.hypersynth_runtime import HypersynthRuntime
from core.lockdown_store import SQLiteLockdownStore
from core.security_lockdown import SecurityLockdown


KEY = b"K" * 32


class LockdownProcessPersistenceTests(unittest.TestCase):
    def test_new_runtime_reads_persisted_emergency_and_denies_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            first = HypersynthRuntime(
                crypto=CryptoIntegrity(KEY),
                admin_authorizer=lambda proof: True,
                lockdown_store=SQLiteLockdownStore(path),
            )
            first.security_lockdown.record_incident("process_boundary", severity=10)

            second = HypersynthRuntime(
                crypto=CryptoIntegrity(KEY),
                admin_authorizer=lambda proof: True,
                lockdown_store=SQLiteLockdownStore(path),
            )

            self.assertEqual(second.security_lockdown.state.mode, SecurityLockdown.EMERGENCY)
            self.assertFalse(second.security_lockdown.permits())

    def test_persisted_normal_state_requires_authoritative_store(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            first.record_incident("incident", severity=10)
            seal = first.export_seal()

            second = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            self.assertEqual(second.state, first.state)
            stale = dict(seal)
            stale["payload"] = stale["payload"].replace(b'"generation":1', b'"generation":0')
            with self.assertRaises(ValueError):
                store.save(stale)

    def test_forged_or_tampered_persistent_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            first.record_incident("tamper", severity=10)
            seal = first.export_seal()
            tampered = dict(seal)
            tampered["tag"] = "0" * 64
            with self.assertRaises(ValueError):
                SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=_TamperedStore(tampered))

    def test_wrong_seal_domain_is_rejected_even_with_valid_authentication(self):
        crypto = CryptoIntegrity(KEY)
        lockdown = SecurityLockdown(crypto, lambda proof: True)
        seal = lockdown.export_seal()
        wrong_domain = crypto.sign("different_domain", {"x": 1}, crypto.next_counter("different_domain"))
        forged_domain = dict(seal)
        forged_domain.update({"domain": wrong_domain.domain, "nonce": wrong_domain.nonce, "counter": wrong_domain.counter, "payload": wrong_domain.payload, "tag": wrong_domain.tag})
        with self.assertRaises(ValueError):
            lockdown.restore_seal(forged_domain)

    def test_runtime_rejects_seal_plus_persistent_store_to_block_replay_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = HypersynthRuntime(crypto=CryptoIntegrity(KEY), admin_authorizer=lambda proof: True, lockdown_store=store)
            normal_seal = first.export_lockdown_seal()
            first.security_lockdown.record_incident("replay", severity=10)

            with self.assertRaises(ValueError):
                HypersynthRuntime(
                    crypto=CryptoIntegrity(KEY),
                    admin_authorizer=lambda proof: True,
                    lockdown_store=SQLiteLockdownStore(path),
                    lockdown_seal=normal_seal,
                )


class _TamperedStore:
    def __init__(self, seal):
        self.seal = seal

    def load(self):
        return self.seal

    def save(self, seal):
        self.seal = seal


if __name__ == "__main__":
    unittest.main()
