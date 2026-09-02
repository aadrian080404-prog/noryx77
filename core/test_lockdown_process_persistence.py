from pathlib import Path
import tempfile
import unittest
import json

from .crypto import CryptoIntegrity
from .hypersynth_runtime import HypersynthRuntime
from .lockdown_store import SQLiteLockdownStore
from .security_lockdown import SecurityLockdown

KEY = b"K" * 32


def _seal_generation(seal):
    return json.loads(seal["payload"].decode("utf-8"))["generation"]


def _with_generation_and_reason(seal, generation, reason):
    result = dict(seal)
    payload = json.loads(seal["payload"].decode("utf-8"))
    payload["generation"] = generation
    payload["reason"] = reason
    result["payload"] = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return result


class LockdownProcessPersistenceTests(unittest.TestCase):
    def test_new_runtime_reads_persisted_emergency_and_denies_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            first.record_incident("persisted", severity=10)
            second = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=SQLiteLockdownStore(path))
            self.assertEqual(second.state.mode, SecurityLockdown.EMERGENCY)
            self.assertFalse(second.permits())

    def test_persisted_generation_cannot_roll_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            first.record_incident("first", severity=10)
            newer = store.load()
            stale = _with_generation_and_reason(newer, 0, "stale")
            with self.assertRaisesRegex(ValueError, "lockdown_store_rollback"):
                store.save(stale, expected_generation=_seal_generation(newer))

    def test_same_generation_writers_cannot_both_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            store = SQLiteLockdownStore(path)
            bootstrap = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
            bootstrap.record_incident("bootstrap", severity=10)
            current = store.load()
            generation = _seal_generation(current)
            first = _with_generation_and_reason(current, generation + 1, "writer_one")
            second = _with_generation_and_reason(current, generation + 1, "writer_two")
            store.save(first, expected_generation=generation)
            with self.assertRaisesRegex(ValueError, "lockdown_store_conflict"):
                store.save(second, expected_generation=generation)

    def test_same_generation_recovery_race_fails_closed_for_loser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lockdown.sqlite3"
            bootstrap = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=SQLiteLockdownStore(path))
            bootstrap.record_incident("recovery_race", severity=10)
            first = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=SQLiteLockdownStore(path))
            second = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=SQLiteLockdownStore(path))
            first_proof = first.admin_challenge()
            second_proof = second.admin_challenge()
            first.recover(first_proof)
            with self.assertRaisesRegex(PermissionError, "admin_recovery_denied"):
                second.recover(second_proof)
            self.assertEqual(first.state.mode, SecurityLockdown.NORMAL)
            self.assertEqual(second.state.mode, SecurityLockdown.EMERGENCY)
            self.assertFalse(second.permits())
            persisted = SQLiteLockdownStore(path).load()
            self.assertEqual(persisted["payload"], first.export_seal()["payload"])

    def test_incident_persistence_failure_fails_closed(self):
        store = _FailingStore()
        lockdown = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
        store.fail_writes = True
        with self.assertRaisesRegex(OSError, "persistence_down"):
            lockdown.record_incident("storage_failure", severity=1)
        self.assertEqual(lockdown.state.mode, SecurityLockdown.EMERGENCY)
        self.assertFalse(lockdown.permits())

    def test_recovery_persistence_failure_fails_closed(self):
        store = _FailingStore()
        lockdown = SecurityLockdown(CryptoIntegrity(KEY), lambda proof: True, state_store=store)
        lockdown.record_incident("bootstrap", severity=10)
        store.fail_writes = True
        proof = lockdown.admin_challenge()
        with self.assertRaisesRegex(OSError, "persistence_down"):
            lockdown.recover(proof)
        self.assertEqual(lockdown.state.mode, SecurityLockdown.EMERGENCY)
        self.assertFalse(lockdown.permits())

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
                HypersynthRuntime(crypto=CryptoIntegrity(KEY), admin_authorizer=lambda proof: True, lockdown_store=SQLiteLockdownStore(path), lockdown_seal=normal_seal)


class _FailingStore:
    def __init__(self):
        self.seal = None
        self.fail_writes = False

    def load(self):
        return self.seal

    def save(self, seal, *, expected_generation=None):
        if self.fail_writes:
            raise OSError("persistence_down")
        self.seal = seal


class _TamperedStore:
    def __init__(self, seal):
        self.seal = seal

    def load(self):
        return self.seal

    def save(self, seal):
        self.seal = seal


if __name__ == "__main__":
    unittest.main()
