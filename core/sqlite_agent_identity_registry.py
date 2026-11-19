"""Durable SQLite trust registry for generation-aware agent identities.

Only public keys and trust metadata are persisted. Private keys remain in an
external KMS/HSM or caller-owned cryptographic boundary.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core.identity import (
    AgentIdentity,
    PUBLIC_KEY_SIZE,
    SIGNATURE_SIZE,
    identity_rotation_message,
)

T = TypeVar("T")
_MAX_GENERATION = (2**64) - 1


class SQLiteAgentIdentityRegistry:
    """Atomic durable trust anchors with dual-proof, monotonic key rotation.

    Revocation is terminal for an agent identifier. Recovery after compromise
    must provision a new identifier through an independently authorized process.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.db_path, timeout=5.0, check_same_thread=False, isolation_level=None
        )
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS agent_identity_trust ("
                "agent_id TEXT PRIMARY KEY, public_key BLOB, generation INTEGER NOT NULL "
                "CHECK(generation >= 1), state TEXT NOT NULL "
                "CHECK(state IN ('active','revoked')), updated_at REAL NOT NULL, "
                "CHECK((state='active' AND public_key IS NOT NULL) OR "
                "(state='revoked' AND public_key IS NULL)))"
            )

    def _begin(self) -> None:
        self._conn.execute("BEGIN IMMEDIATE")

    def register(self, identity: AgentIdentity) -> int:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        with self._lock:
            self._begin()
            try:
                self._conn.execute(
                    "INSERT INTO agent_identity_trust "
                    "(agent_id, public_key, generation, state, updated_at) "
                    "VALUES (?, ?, 1, 'active', ?)",
                    (identity.agent_id, bytes(identity.public_key), time.time()),
                )
                self._conn.commit()
                return 1
            except sqlite3.IntegrityError:
                self._conn.rollback()
                raise ValueError("agent_identity_already_registered") from None
            except Exception:
                self._conn.rollback()
                raise

    def generation(self, agent_id: str) -> int:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            row = self._conn.execute(
                "SELECT generation, state FROM agent_identity_trust WHERE agent_id=?",
                (agent_id,),
            ).fetchone()
        if row is None or row[1] != "active":
            raise PermissionError("agent_identity_not_active")
        return int(row[0])

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            row = self._conn.execute(
                "SELECT public_key, state FROM agent_identity_trust WHERE agent_id=?",
                (identity.agent_id,),
            ).fetchone()
        return row is not None and row[1] == "active" and bytes(row[0]) == identity.public_key

    def rotate_identity(
        self,
        identity: AgentIdentity,
        *,
        expected_generation: int,
        old_key_signature: bytes,
        new_key_signature: bytes,
    ) -> int:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        if (isinstance(expected_generation, bool) or not isinstance(expected_generation, int)
                or not 1 <= expected_generation <= _MAX_GENERATION):
            raise ValueError("invalid_identity_generation")
        if not isinstance(old_key_signature, bytes) or len(old_key_signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_old_key_signature")
        if not isinstance(new_key_signature, bytes) or len(new_key_signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_new_key_signature")

        with self._lock:
            self._begin()
            try:
                row = self._conn.execute(
                    "SELECT public_key, generation, state FROM agent_identity_trust "
                    "WHERE agent_id=?",
                    (identity.agent_id,),
                ).fetchone()
                if row is None or row[2] != "active":
                    raise PermissionError("agent_identity_not_active")
                current_key, current_generation = bytes(row[0]), int(row[1])
                if current_generation != expected_generation:
                    raise PermissionError("identity_generation_conflict")
                if current_generation >= _MAX_GENERATION:
                    raise OverflowError("identity_generation_exhausted")
                if current_key == identity.public_key:
                    raise ValueError("rotation_key_must_change")
                message = identity_rotation_message(
                    identity.agent_id, current_key, identity.public_key, expected_generation
                )
                try:
                    Ed25519PublicKey.from_public_bytes(current_key).verify(
                        old_key_signature, message
                    )
                    Ed25519PublicKey.from_public_bytes(identity.public_key).verify(
                        new_key_signature, message
                    )
                except (InvalidSignature, ValueError, TypeError):
                    raise PermissionError("identity_rotation_proof_invalid") from None
                next_generation = current_generation + 1
                cursor = self._conn.execute(
                    "UPDATE agent_identity_trust SET public_key=?, generation=?, updated_at=? "
                    "WHERE agent_id=? AND generation=? AND state='active'",
                    (bytes(identity.public_key), next_generation, time.time(),
                     identity.agent_id, expected_generation),
                )
                if cursor.rowcount != 1:
                    raise PermissionError("identity_generation_conflict")
                self._conn.commit()
                return next_generation
            except Exception:
                self._conn.rollback()
                raise

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._begin()
            try:
                cursor = self._conn.execute(
                    "UPDATE agent_identity_trust SET public_key=NULL, state='revoked', updated_at=? "
                    "WHERE agent_id=? AND state='active'",
                    (time.time(), agent_id),
                )
                if cursor.rowcount != 1:
                    raise PermissionError("agent_identity_not_active")
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        """Hold a SQLite write reservation across a short verify-and-commit callback."""
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._begin()
            try:
                row = self._conn.execute(
                    "SELECT public_key, state FROM agent_identity_trust WHERE agent_id=?",
                    (agent_id,),
                ).fetchone()
                if row is None or row[1] != "active":
                    raise PermissionError("agent_identity_not_trusted")
                result = callback(AgentIdentity(agent_id, bytes(row[0])))
                self._conn.commit()
                return result
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            self._conn.close()
