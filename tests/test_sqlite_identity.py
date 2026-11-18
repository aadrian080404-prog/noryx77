from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from core.identity import AgentIdentityAuthority
from core.sqlite_identity import SQLiteIdentityRegistry


def test_sqlite_identity_registry_persists_trust_and_revocation(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-a")
    first = SQLiteIdentityRegistry(path)
    first.register(identity)

    reopened = SQLiteIdentityRegistry(path)
    assert reopened.is_trusted(identity)
    reopened.revoke(identity.agent_id)
    assert not first.is_trusted(identity)


def test_independent_registries_reject_duplicate_registration(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-b")
    first = SQLiteIdentityRegistry(path)
    second = SQLiteIdentityRegistry(path)
    first.register(identity)
    with pytest.raises(ValueError, match="agent_identity_already_registered"):
        second.register(identity)


def test_with_trusted_identity_holds_transaction_against_revocation(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-c")
    registry = SQLiteIdentityRegistry(path)
    registry.register(identity)
    callback_started = Event()
    allow_callback_to_finish = Event()

    def callback(current):
        callback_started.set()
        assert allow_callback_to_finish.wait(timeout=5)
        return current.public_key == identity.public_key

    with ThreadPoolExecutor(max_workers=2) as pool:
        verification = pool.submit(
            registry.with_trusted_identity, identity.agent_id, callback
        )
        assert callback_started.wait(timeout=5)
        revocation = pool.submit(registry.revoke, identity.agent_id)
        assert not revocation.done()
        allow_callback_to_finish.set()
        assert verification.result(timeout=5)
        revocation.result(timeout=5)

    assert not registry.is_trusted(identity)


def test_memory_database_is_rejected():
    with pytest.raises(ValueError, match="persistent_identity_database_required"):
        SQLiteIdentityRegistry(":memory:")
