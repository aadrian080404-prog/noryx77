"""Durable key-policy metadata; secret material stays in an external KMS.

This registry never stores private/shared key bytes. Resolution is delegated to
an injected provider only after owner, purpose, generation and authorization
policy checks succeed.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import math
import sqlite3
from typing import Callable, Iterator


PURPOSES = frozenset({
    "OBJECT_AUTH", "NETWORK_HMAC", "TRANSFER_AUTH", "UPDATE_SIGNING",
})


@dataclass(frozen=True)
class KeyPolicy:
    key_id: str
    owner_id: str
    purpose: str
    generation: int
    state: str


class DurableKeyPolicyRegistry:
    def __init__(self, database: str, *, authorize: Callable[..., bool],
                 key_resolver: Callable[[str], bytes], timeout: float = 5.0) -> None:
        if not isinstance(database, str) or not database:
            raise ValueError("database_path_required")
        if not callable(authorize) or not callable(key_resolver):
            raise ValueError("authorization_and_key_resolver_required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout_must_be_finite_and_positive")
        self.database = database
        self.authorize = authorize
        self.key_resolver = key_resolver
        self.timeout = float(timeout)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_key_policies (
                key_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                generation INTEGER NOT NULL CHECK(generation > 0),
                state TEXT NOT NULL CHECK(state IN ('ACTIVE','REVOKED')),
                UNIQUE(owner_id,purpose,generation)
            )""")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    @staticmethod
    def _validate(owner_id: str, purpose: str) -> None:
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id_required")
        if purpose not in PURPOSES:
            raise ValueError("unsupported_key_purpose")

    def register(self, key_id: str, owner_id: str, purpose: str, generation: int) -> KeyPolicy:
        self._validate(owner_id, purpose)
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("key_id_required")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation <= 0:
            raise ValueError("generation_must_be_positive_integer")
        if not self.authorize("REGISTER", owner_id, purpose, key_id, generation):
            raise PermissionError("key_registration_not_authorized")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT owner_id,purpose,generation,state FROM matrix_key_policies WHERE key_id=?",
                (key_id,),
            ).fetchone()
            if existing is not None:
                db.rollback()
                if existing == (owner_id, purpose, generation, "ACTIVE"):
                    return KeyPolicy(key_id, owner_id, purpose, generation, "ACTIVE")
                raise PermissionError("key_id_already_bound")
            latest = db.execute(
                "SELECT MAX(generation) FROM matrix_key_policies WHERE owner_id=? AND purpose=?",
                (owner_id, purpose),
            ).fetchone()[0] or 0
            if generation <= latest:
                db.rollback()
                raise PermissionError("key_generation_not_monotonic")
            db.execute(
                "INSERT INTO matrix_key_policies VALUES(?,?,?,?,'ACTIVE')",
                (key_id, owner_id, purpose, generation),
            )
            db.commit()
        return KeyPolicy(key_id, owner_id, purpose, generation, "ACTIVE")

    def revoke(self, key_id: str, owner_id: str, *, generation: int) -> KeyPolicy:
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id_required")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation <= 0:
            raise ValueError("generation_must_be_positive_integer")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT owner_id,purpose,generation,state FROM matrix_key_policies WHERE key_id=?",
                (key_id,),
            ).fetchone()
            if row is None or row[0] != owner_id:
                db.rollback()
                raise PermissionError("key_owner_binding_mismatch")
            if generation <= row[2]:
                db.rollback()
                raise PermissionError("key_generation_not_monotonic")
            if not self.authorize("REVOKE", owner_id, row[1], key_id, generation):
                db.rollback()
                raise PermissionError("key_revocation_not_authorized")
            db.execute(
                "UPDATE matrix_key_policies SET generation=?,state='REVOKED' WHERE key_id=?",
                (generation, key_id),
            )
            db.commit()
        return KeyPolicy(key_id, owner_id, row[1], generation, "REVOKED")

    def resolve(self, key_id: str, owner_id: str, purpose: str) -> bytes:
        self._validate(owner_id, purpose)
        with self._connection() as db:
            row = db.execute(
                "SELECT owner_id,purpose,generation,state FROM matrix_key_policies WHERE key_id=?",
                (key_id,),
            ).fetchone()
        if row is None or row[0] != owner_id or row[1] != purpose:
            raise PermissionError("key_scope_mismatch")
        if row[3] != "ACTIVE":
            raise PermissionError("key_revoked")
        if not self.authorize("RESOLVE", owner_id, purpose, key_id, row[2]):
            raise PermissionError("key_resolution_not_authorized")
        key = self.key_resolver(key_id)
        if not isinstance(key, bytes) or len(key) < 32:
            raise PermissionError("key_provider_returned_invalid_material")
        return key

    def get(self, key_id: str) -> KeyPolicy | None:
        with self._connection() as db:
            row = db.execute(
                "SELECT owner_id,purpose,generation,state FROM matrix_key_policies WHERE key_id=?",
                (key_id,),
            ).fetchone()
        if row is None:
            return None
        return KeyPolicy(key_id, row[0], row[1], row[2], row[3])
