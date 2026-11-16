import sqlite3
import threading

import pytest

from core.key_lifecycle import KeyRecord, KeyState, SQLiteKeyLifecycle


def test_sqlite_key_lifecycle_survives_restart(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    first = SQLiteKeyLifecycle(path)
    assert first.register("memory-master") == KeyRecord("memory-master", 1, KeyState.ACTIVE)
    assert first.rotate("memory-master") == KeyRecord("memory-master", 2, KeyState.ACTIVE)
    first.close()

    second = SQLiteKeyLifecycle(path)
    try:
        assert second.require_active("memory-master").version == 2
        assert second.snapshot() == (KeyRecord("memory-master", 2, KeyState.ACTIVE),)
    finally:
        second.close()


def test_sqlite_key_lifecycle_persists_retirement_and_revocation(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    lifecycle = SQLiteKeyLifecycle(path)
    lifecycle.register("signing")
    assert lifecycle.retire("signing").state is KeyState.RETIRING
    with pytest.raises(PermissionError, match="key_not_active"):
        lifecycle.require_active("signing")
    with pytest.raises(PermissionError, match="retiring_key_cannot_reactivate"):
        lifecycle.rotate("signing")
    assert lifecycle.revoke("signing").state is KeyState.REVOKED
    lifecycle.close()

    reopened = SQLiteKeyLifecycle(path)
    try:
        assert reopened.snapshot() == (KeyRecord("signing", 1, KeyState.REVOKED),)
        with pytest.raises(PermissionError, match="revoked_key_cannot_rotate"):
            reopened.rotate("signing")
    finally:
        reopened.close()


def test_sqlite_key_lifecycle_never_persists_key_material(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    lifecycle = SQLiteKeyLifecycle(path)
    lifecycle.register("kms://tenant/signing-key")
    lifecycle.close()

    connection = sqlite3.connect(path)
    try:
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='key_lifecycle'"
        ).fetchone()[0]
        row = connection.execute("SELECT * FROM key_lifecycle").fetchone()
    finally:
        connection.close()
    assert "key_material" not in schema
    assert row == ("kms://tenant/signing-key", 1, "active")


def test_sqlite_key_lifecycle_rejects_invalid_ids_and_versions(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    try:
        for invalid in ("", "  ", "x" * 257, "\ud800"):
            with pytest.raises(ValueError, match="invalid_key_id"):
                lifecycle.register(invalid)
        for invalid in (True, 0, -1, 1.5):
            with pytest.raises(ValueError, match="invalid_key_version"):
                lifecycle.register("key", version=invalid)
    finally:
        lifecycle.close()


def test_sqlite_key_lifecycle_revocation_is_visible_across_connections(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    first = SQLiteKeyLifecycle(path)
    first.register("shared")
    second = SQLiteKeyLifecycle(path)
    try:
        assert second.require_active("shared").version == 1
        first.revoke("shared")
        with pytest.raises(PermissionError, match="key_not_active"):
            second.require_active("shared")
    finally:
        first.close()
        second.close()


def test_sqlite_key_lifecycle_concurrent_rotation_is_serialized(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    first = SQLiteKeyLifecycle(path)
    first.register("parallel")
    second = SQLiteKeyLifecycle(path)
    errors = []

    def rotate(manager):
        try:
            manager.rotate("parallel")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=rotate, args=(first if i % 2 else second,))
               for i in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    try:
        assert errors == []
        assert first.require_active("parallel").version == 13
    finally:
        first.close()
        second.close()


def test_sqlite_key_lifecycle_fails_after_close(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.close()
    with pytest.raises(RuntimeError, match="key_lifecycle_closed"):
        lifecycle.snapshot()
