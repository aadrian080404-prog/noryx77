import sqlite3

import pytest

from core.durable_key_lifecycle import DurableKeyLifecycle
from core.key_lifecycle import KeyState


KEY = b"durable-key-lifecycle-test-key-material-32-bytes"
KEY_ID = "metadata-integrity-v1"


def open_store(path):
    return DurableKeyLifecycle(str(path), integrity_key=KEY, key_id=KEY_ID)


def test_key_lifecycle_operations_survive_restart(tmp_path):
    path = tmp_path / "keys.sqlite"
    lifecycle = open_store(path)
    lifecycle.register("kms-root")
    assert lifecycle.rotate("kms-root").version == 2
    assert lifecycle.retire("kms-root").state is KeyState.RETIRING
    assert lifecycle.revoke("kms-root").state is KeyState.REVOKED
    lifecycle.close()

    recovered = open_store(path)
    record = recovered.snapshot()[0]
    assert record.key_id == "kms-root"
    assert record.version == 2
    assert record.state is KeyState.REVOKED
    with pytest.raises(PermissionError, match="key_not_active"):
        recovered.require_active("kms-root")
    recovered.close()


def test_invalid_transition_is_not_persisted(tmp_path):
    path = tmp_path / "keys.sqlite"
    lifecycle = open_store(path)
    lifecycle.register("kms-root")
    lifecycle.revoke("kms-root")
    with pytest.raises(PermissionError, match="revoked_key_cannot_rotate"):
        lifecycle.rotate("kms-root")
    lifecycle.close()

    recovered = open_store(path)
    assert recovered.snapshot()[0].state is KeyState.REVOKED
    recovered.close()


def test_tampered_key_lifecycle_event_fails_closed(tmp_path):
    path = tmp_path / "keys.sqlite"
    lifecycle = open_store(path)
    lifecycle.register("kms-root")
    lifecycle.close()

    db = sqlite3.connect(path)
    db.execute("UPDATE key_lifecycle_events SET event_json=? WHERE sequence=1",
               ('{"key_id":"kms-root","operation":"revoke","state":"revoked","version":1}',))
    db.commit()
    db.close()
    with pytest.raises(RuntimeError, match="integrity_failure"):
        open_store(path)


def test_closed_key_lifecycle_is_not_durable(tmp_path):
    lifecycle = open_store(tmp_path / "keys.sqlite")
    assert lifecycle.durable
    lifecycle.close()
    assert not lifecycle.durable
    with pytest.raises(RuntimeError, match="closed"):
        lifecycle.register("kms-root")
