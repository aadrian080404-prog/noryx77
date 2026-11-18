from concurrent.futures import ThreadPoolExecutor

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
    entered = []

    def verify():
        return registry.with_trusted_identity(
            identity.agent_id,
            lambda current: entered.append(current.public_key) or True,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert pool.submit(verify).result(timeout=5)
        pool.submit(registry.revoke, identity.agent_id).result(timeout=5)

    assert entered == [identity.public_key]
    assert not registry.is_trusted(identity)


def test_memory_database_is_rejected():
    with pytest.raises(ValueError, match="persistent_identity_database_required"):
        SQLiteIdentityRegistry(":memory:")
