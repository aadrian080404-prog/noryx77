import sqlite3

import pytest

from core.durable_identity import DurableIdentityRegistry
from core.identity import AgentIdentityAuthority


KEY = b"identity-registry-test-key-material-at-least-32-bytes"
KEY_ID = "identity-test-v1"


def test_registration_and_revocation_survive_restart(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, private_key = AgentIdentityAuthority.generate("agent-a")
    registry = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    registry.register(identity)
    assert registry.is_trusted(identity)
    registry.close()

    recovered = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    assert recovered.is_trusted(identity)
    recovered.revoke("agent-a")
    assert not recovered.is_trusted(identity)
    recovered.close()

    final = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    assert not final.is_trusted(identity)
    final.close()


def test_duplicate_registration_is_rejected_without_corrupting_journal(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    registry = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    registry.register(identity)
    with pytest.raises(ValueError, match="already_registered"):
        registry.register(identity)
    registry.close()
    recovered = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    assert recovered.is_trusted(identity)
    recovered.close()


def test_tampered_identity_event_fails_closed(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    registry = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    registry.register(identity)
    registry.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE identity_events SET event_json = ? WHERE sequence = 1", ('{"agent_id":"other","public_key":null,"type":"revoke"}',))
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="integrity_failure"):
        DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)


def test_wrong_key_fails_closed(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    registry = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    registry.register(identity)
    registry.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        DurableIdentityRegistry(path, integrity_key=b"another-key-material-at-least-32-bytes-long", key_id=KEY_ID)



def test_closed_identity_registry_fails_closed(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    registry = DurableIdentityRegistry(path, integrity_key=KEY, key_id=KEY_ID)
    registry.register(identity)
    registry.close()
    assert not registry.durable
    with pytest.raises(RuntimeError, match="closed"):
        registry.is_trusted(identity)
    with pytest.raises(RuntimeError, match="closed"):
        registry.with_trusted_identity("agent-a", lambda value: value)
