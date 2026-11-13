"""Optional encrypted SQLite persistence for NORYX7 memory items.

AES-GCM protects serialized memory content at rest. The key must be injected
from an external secret manager and is never stored in the database.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .memory import MemoryItem, MemoryStore


SCHEMA_VERSION = 1
NONCE_SIZE = 12


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


class SQLiteEncryptedMemoryStore(MemoryStore):
    """Encrypted single-host persistence preserving MemoryStore access semantics."""

    def __init__(
        self,
        path: str,
        *,
        encryption_key: bytes,
        key_id: str,
        max_items: int = 10_000,
    ) -> None:
        if not isinstance(path, str) or not path.strip() or not os.path.isabs(path):
            raise ValueError("absolute_memory_store_path_required")
        if os.path.islink(path):
            raise ValueError("memory_store_symlink_rejected")
        if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
            raise ValueError("memory_store_requires_256_bit_key")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("invalid_memory_key_id")
        super().__init__(max_items=max_items)
        self.path = path
        self._key_id = key_id
        self._cipher = AESGCM(bytes(encryption_key))
        self._failed = False
        self._db = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute("PRAGMA secure_delete=ON")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS memory_store_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS encrypted_memory_items ("
                "memory_id TEXT PRIMARY KEY, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, "
                "key_id TEXT NOT NULL) WITHOUT ROWID"
            )
            self._initialize_metadata()
            self._recover()
            if os.name == "posix":
                os.chmod(path, 0o600)
        except Exception:
            self._db.close()
            self._failed = True
            raise

    @property
    def durable(self) -> bool:
        return not self._failed

    def _initialize_metadata(self) -> None:
        rows = dict(self._db.execute("SELECT key,value FROM memory_store_meta").fetchall())
        if not rows:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute(
                    "INSERT INTO memory_store_meta(key,value) VALUES('schema_version',?)",
                    (str(SCHEMA_VERSION),),
                )
                self._db.execute(
                    "INSERT INTO memory_store_meta(key,value) VALUES('key_id',?)",
                    (self._key_id,),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
            return
        if rows.get("schema_version") != str(SCHEMA_VERSION):
            raise RuntimeError("unsupported_memory_store_schema")
        if rows.get("key_id") != self._key_id:
            raise RuntimeError("memory_store_key_id_mismatch")

    def _aad(self, memory_id: str) -> bytes:
        return f"NORYX7_MEMORY_V1:{self._key_id}:{memory_id}".encode("utf-8")

    @staticmethod
    def _serialize(item: MemoryItem) -> bytes:
        return _canonical({
            "memory_id": item.memory_id,
            "content": item.content,
            "kind": item.kind,
            "source": item.source,
            "importance": float(item.importance),
            "execution_id": item.execution_id,
        })

    @staticmethod
    def _deserialize(payload: bytes) -> MemoryItem:
        try:
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, dict) or set(value) != {
                "memory_id", "content", "kind", "source", "importance", "execution_id"
            }:
                raise ValueError("memory_payload_schema_mismatch")
            return MemoryItem(**value)
        except (UnicodeError, ValueError, TypeError) as exc:
            raise RuntimeError("memory_store_payload_invalid") from exc

    def _ensure_healthy(self) -> None:
        if self._failed:
            raise RuntimeError("memory_store_failed_closed")

    def _recover(self) -> None:
        rows = self._db.execute(
            "SELECT memory_id,nonce,ciphertext,key_id FROM encrypted_memory_items ORDER BY memory_id"
        ).fetchall()
        for memory_id, nonce, ciphertext, key_id in rows:
            if key_id != self._key_id or not isinstance(nonce, bytes) or len(nonce) != NONCE_SIZE:
                raise RuntimeError("memory_store_record_metadata_invalid")
            try:
                plaintext = self._cipher.decrypt(nonce, ciphertext, self._aad(memory_id))
            except Exception as exc:
                raise RuntimeError("memory_store_authentication_failure") from exc
            item = self._deserialize(plaintext)
            if item.memory_id != memory_id:
                raise RuntimeError("memory_store_identity_binding_failure")
            super().put(item)

    def put(self, item: MemoryItem) -> None:
        self._ensure_healthy()
        if not isinstance(item, MemoryItem):
            raise ValueError("valid memory item with memory_id required")
        # Validate JSON compatibility before mutating the in-memory view.
        plaintext = self._serialize(item)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = self._cipher.encrypt(nonce, plaintext, self._aad(item.memory_id))
        super().put(item)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute(
                "INSERT INTO encrypted_memory_items(memory_id,nonce,ciphertext,key_id) "
                "VALUES(?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET "
                "nonce=excluded.nonce,ciphertext=excluded.ciphertext,key_id=excluded.key_id",
                (item.memory_id, sqlite3.Binary(nonce), sqlite3.Binary(ciphertext), self._key_id),
            )
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            self._failed = True
            raise

    def get(self, memory_id: str, *, execution_id: str | None = None):
        self._ensure_healthy()
        return super().get(memory_id, execution_id=execution_id)

    def list(self, kind: str | None = None, *, execution_id: str | None = None):
        self._ensure_healthy()
        return super().list(kind, execution_id=execution_id)

    def delete(self, memory_id: str) -> bool:
        self._ensure_healthy()
        if not self._valid_memory_id(memory_id):
            return False
        try:
            self._db.execute("BEGIN IMMEDIATE")
            cursor = self._db.execute(
                "DELETE FROM encrypted_memory_items WHERE memory_id=?", (memory_id,)
            )
            self._db.execute("COMMIT")
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            self._failed = True
            raise
        super().delete(memory_id)
        return cursor.rowcount > 0

    def __len__(self) -> int:
        self._ensure_healthy()
        return super().__len__()

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
        self._failed = True
