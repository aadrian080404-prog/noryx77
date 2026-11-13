from __future__ import annotations

import sqlite3

import pytest

from .memory import MemoryItem
from .sqlite_memory import SQLiteEncryptedMemoryStore


def _store(path, key=b"m" * 32, key_id="memory-kms-v1"):
    return SQLiteEncryptedMemoryStore(
        str(path), encryption_key=key, key_id=key_id, max_items=20,
    )


def test_encrypted_memory_persists_and_does_not_store_plaintext(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = _store(path)
    item = MemoryItem(
        "mem-1",
        {"private_note": "distinctive-secret-content-9137", "facts": [1, 2, 3]},
        kind="long_term",
        source="verified-source",
        importance=0.9,
        execution_id="exec-1",
    )
    store.put(item)
    assert store.get("mem-1", execution_id="exec-1") == item
    store.close()

    raw = path.read_bytes()
    assert b"distinctive-secret-content-9137" not in raw
    recovered = _store(path)
    assert recovered.get("mem-1", execution_id="exec-1") == item
    assert recovered.get("mem-1", execution_id="exec-2") is None
    recovered.close()


def test_encrypted_memory_rejects_wrong_key_and_key_id(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = _store(path)
    store.put(MemoryItem("mem-1", "secret", execution_id="exec-1"))
    store.close()

    with pytest.raises(RuntimeError, match="authentication_failure"):
        _store(path, key=b"x" * 32)
    with pytest.raises(RuntimeError, match="key_id_mismatch"):
        _store(path, key_id="rotated-key")


def test_encrypted_memory_detects_ciphertext_tampering(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = _store(path)
    store.put(MemoryItem("mem-1", "secret", execution_id="exec-1"))
    store.close()

    db = sqlite3.connect(path)
    nonce, ciphertext = db.execute(
        "SELECT nonce,ciphertext FROM encrypted_memory_items WHERE memory_id='mem-1'"
    ).fetchone()
    altered = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
    db.execute(
        "UPDATE encrypted_memory_items SET ciphertext=? WHERE memory_id='mem-1'",
        (sqlite3.Binary(altered),),
    )
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="authentication_failure"):
        _store(path)


def test_encrypted_memory_delete_survives_restart(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = _store(path)
    store.put(MemoryItem("mem-1", "secret", execution_id="exec-1"))
    assert store.delete("mem-1") is True
    store.close()

    recovered = _store(path)
    assert recovered.get("mem-1") is None
    assert len(recovered) == 0
    recovered.close()


def test_encrypted_memory_rejects_non_json_content_before_mutation(tmp_path):
    store = _store(tmp_path / "memory.sqlite")
    with pytest.raises(TypeError):
        store.put(MemoryItem("mem-1", object(), execution_id="exec-1"))
    assert len(store) == 0
    store.close()


def test_encrypted_memory_enforces_capacity_after_recovery(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = _store(path)
    store.put(MemoryItem("mem-1", "one"))
    store.put(MemoryItem("mem-2", "two"))
    store.close()

    with pytest.raises(MemoryError, match="memory_capacity_exceeded"):
        SQLiteEncryptedMemoryStore(
            str(path), encryption_key=b"m" * 32,
            key_id="memory-kms-v1", max_items=1,
        )
