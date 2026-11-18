import os
import stat

import pytest

from core.offline import SQLiteOfflineSyncQueue


class TestCipher:
    def encrypt(self, plaintext: bytes, *, aad: bytes) -> bytes:
        return b"ciphertext:" + aad + b":" + plaintext

    def decrypt(self, ciphertext: bytes, *, aad: bytes) -> bytes:
        prefix = b"ciphertext:" + aad + b":"
        if not ciphertext.startswith(prefix):
            raise ValueError("authentication_failed")
        return ciphertext[len(prefix):]


def test_sqlite_offline_queue_rejects_in_memory_database():
    with pytest.raises(ValueError, match="persistent_offline_database_required"):
        SQLiteOfflineSyncQueue(":memory:", TestCipher())


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permission semantics required")
def test_sqlite_offline_queue_restricts_database_file_permissions(tmp_path):
    database = tmp_path / "offline-queue.sqlite3"
    database.write_bytes(b"")
    database.chmod(0o644)

    queue = SQLiteOfflineSyncQueue(str(database), TestCipher())
    try:
        assert stat.S_IMODE(database.stat().st_mode) == 0o600
    finally:
        queue.close()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permission semantics required")
def test_sqlite_offline_queue_restricts_permissions_on_existing_database(tmp_path):
    database = tmp_path / "existing-offline-queue.sqlite3"
    queue = SQLiteOfflineSyncQueue(str(database), TestCipher())
    queue.close()
    database.chmod(0o644)

    reopened = SQLiteOfflineSyncQueue(str(database), TestCipher())
    try:
        assert stat.S_IMODE(database.stat().st_mode) == 0o600
    finally:
        reopened.close()



def test_sqlite_offline_queue_rejects_capacity_configuration_mismatch(tmp_path):
    database = tmp_path / "offline-capacity.sqlite3"
    first = SQLiteOfflineSyncQueue(str(database), TestCipher(), max_items=4)
    first.close()

    with pytest.raises(ValueError, match="offline_queue_configuration_mismatch"):
        SQLiteOfflineSyncQueue(str(database), TestCipher(), max_items=5)
