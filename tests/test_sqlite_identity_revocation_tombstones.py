import sqlite3

import pytest

from core.identity import AgentIdentityAuthority
from core.sqlite_identity import SQLiteIdentityRegistry


def test_revocation_is_permanent_across_restart_and_re_registration(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-revoked")
    replacement, _ = AgentIdentityAuthority.generate("worker-revoked")

    registry = SQLiteIdentityRegistry(path)
    registry.register(identity)
    assert registry.is_revoked(identity.agent_id) is False
    registry.revoke(identity.agent_id)
    assert registry.is_revoked(identity.agent_id) is True
    assert not registry.is_trusted(identity)
    registry.close() if callable(getattr(registry, "close", None)) else None

    reopened = SQLiteIdentityRegistry(path)
    assert not reopened.is_trusted(identity)
    with pytest.raises(PermissionError, match="agent_identity_permanently_revoked"):
        reopened.register(replacement)
    with pytest.raises(PermissionError, match="agent_identity_permanently_revoked"):
        reopened.with_trusted_identity(identity.agent_id, lambda current: True)


def test_revocation_of_unknown_identity_prevents_later_registration(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-never-trusted")
    registry = SQLiteIdentityRegistry(path)
    registry.revoke(identity.agent_id)

    with pytest.raises(PermissionError, match="agent_identity_permanently_revoked"):
        registry.register(identity)


def test_schema_v1_is_migrated_to_tombstone_schema_v2(tmp_path):
    path = tmp_path / "legacy-identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-legacy")
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE noryx7_identity_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE noryx7_trusted_agents (agent_id TEXT PRIMARY KEY, public_key BLOB NOT NULL)"
        )
        connection.execute(
            "INSERT INTO noryx7_identity_metadata(key, value) VALUES('schema_version', '1')"
        )
        connection.execute(
            "INSERT INTO noryx7_trusted_agents(agent_id, public_key) VALUES(?, ?)",
            (identity.agent_id, sqlite3.Binary(identity.public_key)),
        )
        connection.commit()
    finally:
        connection.close()

    registry = SQLiteIdentityRegistry(path)
    assert registry.is_trusted(identity)
    connection = sqlite3.connect(path)
    try:
        version = connection.execute(
            "SELECT value FROM noryx7_identity_metadata WHERE key='schema_version'"
        ).fetchone()[0]
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='noryx7_revoked_agents'"
        ).fetchone()
    finally:
        connection.close()
    assert version == "2"
    assert table is not None


def test_repeated_revocation_preserves_original_tombstone_timestamp(tmp_path):
    path = tmp_path / "identity.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-repeat-revoke")
    registry = SQLiteIdentityRegistry(path)
    registry.register(identity)
    registry.revoke(identity.agent_id)

    connection = sqlite3.connect(path)
    try:
        first = connection.execute(
            "SELECT revoked_at FROM noryx7_revoked_agents WHERE agent_id = ?",
            (identity.agent_id,),
        ).fetchone()[0]
    finally:
        connection.close()

    registry.revoke(identity.agent_id)

    connection = sqlite3.connect(path)
    try:
        second = connection.execute(
            "SELECT revoked_at FROM noryx7_revoked_agents WHERE agent_id = ?",
            (identity.agent_id,),
        ).fetchone()[0]
    finally:
        connection.close()

    assert first == second
    assert not registry.is_trusted(identity)



def test_agent_registry_exposes_membership_for_federation_admission(tmp_path):
    path = tmp_path / "identity-membership.sqlite3"
    identity, _ = AgentIdentityAuthority.generate("worker-membership")
    registry = SQLiteIdentityRegistry(path)

    assert registry.is_registered(identity.agent_id) is False
    registry.register(identity)
    assert registry.is_registered(identity.agent_id) is True
    registry.revoke(identity.agent_id)
    assert registry.is_registered(identity.agent_id) is False

    reopened = SQLiteIdentityRegistry(path)
    assert reopened.is_registered(identity.agent_id) is False
