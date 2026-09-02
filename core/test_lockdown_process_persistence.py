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
            with self.assertRaises(ValueError):
                store.save({**seal, "payload": seal["payload"].replace(b'"generation":1', b'"generation":0')})

    def test_forged_or_tampered_persistent_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            first.record_incident("tamper", severity=10)
            seal = first.export_seal()
            tampered = dict(seal)
            tampered["tag"] = "0" * 64
            store.save(tampered) if False else None
            with self.assertRaises(ValueError):
                SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=_TamperedStore(tampered))


class _TamperedStore:
    def __init__(self, seal):
        self.seal = seal

    def load(self):
        return self.seal

    def save(self, seal):
        self.seal = seal


if __name__ == "__main__":
    unittest.main()
