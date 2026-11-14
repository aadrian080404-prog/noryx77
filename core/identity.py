"""Cryptographic agent identity, trust anchors, and signed attestation primitives."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable, Final, TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


IDENTITY_VERSION: Final[int] = 1
PUBLIC_KEY_SIZE: Final[int] = 32
SIGNATURE_SIZE: Final[int] = 64
MAX_ID_SIZE: Final[int] = 1024
MAX_STATEMENT_SIZE: Final[int] = 16 * 1024 * 1024
_DOMAIN: Final[bytes] = b"noryx7/agent-identity/v1/"
T = TypeVar("T")


def _identity_field(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_ID_SIZE:
        raise ValueError("identity_field_size_exceeded")
    return len(encoded).to_bytes(4, "big") + encoded


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    public_key: bytes
    version: int = IDENTITY_VERSION

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.agent_id, str)
            and bool(self.agent_id.strip())
            and len(self.agent_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.public_key, bytes)
            and len(self.public_key) == PUBLIC_KEY_SIZE
            and self.version == IDENTITY_VERSION
        )


@dataclass(frozen=True)
class AgentAttestation:
    identity: AgentIdentity
    statement: bytes
    signature: bytes

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.identity, AgentIdentity)
            and self.identity.is_well_formed()
            and isinstance(self.statement, bytes)
            and len(self.statement) <= MAX_STATEMENT_SIZE
            and isinstance(self.signature, bytes)
            and len(self.signature) == SIGNATURE_SIZE
        )


def _identity_bytes(identity: AgentIdentity) -> bytes:
    if not identity.is_well_formed():
        raise ValueError("invalid_agent_identity")
    return _DOMAIN + identity.version.to_bytes(2, "big") + _identity_field(identity.agent_id) + identity.public_key


def _attestation_message(identity: AgentIdentity, statement: bytes) -> bytes:
    if not isinstance(statement, bytes):
        raise TypeError("statement_must_be_bytes")
    if len(statement) > MAX_STATEMENT_SIZE:
        raise ValueError("statement_size_exceeded")
    return _identity_bytes(identity) + len(statement).to_bytes(8, "big") + statement


class IdentityRegistry:
    """Explicit trust-anchor registry mapping agent IDs to approved public keys."""

    def __init__(self):
        self._keys: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def register(self, identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        with self._lock:
            if identity.agent_id in self._keys:
                raise ValueError("agent_identity_already_registered")
            self._keys[identity.agent_id] = bytes(identity.public_key)

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._keys.pop(agent_id, None)

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            return self._keys.get(identity.agent_id) == identity.public_key

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        """Run a short verification/commit critical section against one live key.

        Revocation and key replacement cannot interleave with the callback. The
        callback is intended for bounded cryptographic verification and state
        commit only; it must not perform external I/O or invoke agent code.
        """
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            public_key = self._keys.get(agent_id)
            if public_key is None:
                raise PermissionError("agent_identity_not_trusted")
            return callback(AgentIdentity(agent_id, bytes(public_key)))


class AgentIdentityAuthority:
    """Creates and verifies Ed25519-backed agent identities and attestations."""

    @staticmethod
    def generate(agent_id: str) -> tuple[AgentIdentity, Ed25519PrivateKey]:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if len(agent_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("agent_id_size_exceeded")
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return AgentIdentity(agent_id, public_key), private_key

    @staticmethod
    def sign(identity: AgentIdentity, private_key: Ed25519PrivateKey, statement: bytes) -> AgentAttestation:
        if not identity.is_well_formed() or not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("invalid_identity_signing_context")
        raw_public = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        if raw_public != identity.public_key:
            raise ValueError("identity_private_key_mismatch")
        signature = private_key.sign(_attestation_message(identity, statement))
        return AgentAttestation(identity, bytes(statement), signature)

    @staticmethod
    def verify(attestation: AgentAttestation, registry: IdentityRegistry | None = None) -> bool:
        if not isinstance(attestation, AgentAttestation) or not attestation.is_well_formed():
            return False
        if registry is not None and not registry.is_trusted(attestation.identity):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(attestation.identity.public_key).verify(
                attestation.signature,
                _attestation_message(attestation.identity, attestation.statement),
            )
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    @staticmethod
    def verify_identity(identity: AgentIdentity, registry: IdentityRegistry | None = None) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        return registry is None or registry.is_trusted(identity)


class SQLiteIdentityRegistry:
    """Durable trust-anchor registry with cross-process revocation ordering.

    Public keys only are stored here. Private signing keys remain in an
    external key provider. The callback passed to with_trusted_identity must
    be short and bounded; it executes while a SQLite write transaction
    serializes it against revocation from other connections/processes.
    """

    _ACTIVE = "active"
    _REVOKED = "revoked"

    def __init__(self, path: str) -> None:
        import sqlite3
        from pathlib import Path

        if not isinstance(path, str) or not path.strip():
            raise ValueError("identity_registry_database_path_required")
        self._lock = threading.RLock()
        self._closed = False
        self._db = sqlite3.connect(
            str(Path(path)), timeout=30, isolation_level=None, check_same_thread=False
        )
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=30000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS agent_identity_trust ("
                "agent_id TEXT PRIMARY KEY, public_key BLOB NOT NULL, "
                "version INTEGER NOT NULL, state TEXT NOT NULL "
                "CHECK(state IN ('active','revoked')))"
            )
            self._validate_rows()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("identity_registry_closed")

    def _validate_rows(self) -> None:
        for agent_id, public_key, version, state in self._db.execute(
            "SELECT agent_id, public_key, version, state FROM agent_identity_trust"
        ):
            if (
                not isinstance(agent_id, str) or not agent_id.strip()
                or len(agent_id.encode("utf-8")) > MAX_ID_SIZE
                or not isinstance(public_key, bytes) or len(public_key) != PUBLIC_KEY_SIZE
                or isinstance(version, bool) or not isinstance(version, int)
                or version != IDENTITY_VERSION
                or state not in {self._ACTIVE, self._REVOKED}
            ):
                raise RuntimeError("identity_registry_database_corrupt")

    @staticmethod
    def _validate_identity(identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")

    def register(self, identity: AgentIdentity) -> None:
        self._validate_identity(identity)
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO agent_identity_trust(agent_id,public_key,version,state) "
                    "VALUES(?,?,?,?)",
                    (identity.agent_id, identity.public_key, identity.version, self._ACTIVE),
                )
                self._db.execute("COMMIT")
            except Exception as exc:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("agent_identity_already_registered") from exc
                raise

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._ensure_open()
            self._db.execute(
                "UPDATE agent_identity_trust SET state=? WHERE agent_id=?",
                (self._REVOKED, agent_id),
            )

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            self._ensure_open()
            row = self._db.execute(
                "SELECT public_key,state FROM agent_identity_trust WHERE agent_id=?",
                (identity.agent_id,),
            ).fetchone()
            return row is not None and row[1] == self._ACTIVE and row[0] == identity.public_key

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT public_key,version,state FROM agent_identity_trust WHERE agent_id=?",
                    (agent_id,),
                ).fetchone()
                if row is None or row[2] != self._ACTIVE:
                    raise PermissionError("agent_identity_not_trusted")
                identity = AgentIdentity(agent_id, bytes(row[0]), int(row[1]))
                result = callback(identity)
                self._db.execute("COMMIT")
                return result
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def snapshot(self) -> tuple[AgentIdentity, ...]:
        with self._lock:
            self._ensure_open()
            rows = self._db.execute(
                "SELECT agent_id,public_key,version FROM agent_identity_trust "
                "WHERE state=? ORDER BY agent_id",
                (self._ACTIVE,),
            ).fetchall()
            return tuple(AgentIdentity(agent_id, bytes(public_key), version)
                         for agent_id, public_key, version in rows)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
