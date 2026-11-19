"""Principal-bound durable one-shot grants for local action dispatch.

This is an isolated authorization primitive. It does not enable gateway ingress
or translate federated capability strings into local permissions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Callable

from .actions import AuthorizationAuthority
from .contracts import ActionSpec
from .principal_identity import PrincipalIdentity, PrincipalIdentityRegistry


@dataclass(frozen=True)
class PrincipalAuthorizationGrant:
    principal_id: str
    principal_key_fingerprint: str
    action_fingerprint: str
    execution_id: str
    nonce: bytes
    expires_at: int
    signature: str


class PrincipalAuthorizationAuthority:
    """Issues and durably consumes grants bound to principal, key, action and run.

    Consumption is at-most-once. The grant is committed before executor dispatch;
    a process crash after consumption can lose the action, but cannot authorize a
    duplicate dispatch. The principal registry's trusted-principal transaction is
    held across consumption and dispatch so revocation cannot race the boundary.
    """

    def __init__(
        self,
        secret: bytes,
        database_path: str | os.PathLike[str],
        principal_registry: PrincipalIdentityRegistry,
        *,
        clock: Callable[[], int] = lambda: int(time.time()),
        max_ttl_seconds: int = 300,
    ) -> None:
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("authorization_secret_too_short")
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("persistent_grant_database_required")
        raw_path = os.fspath(database_path)
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path == ":memory:":
            raise ValueError("persistent_grant_database_required")
        if not callable(clock):
            raise ValueError("trusted_clock_required")
        if (isinstance(max_ttl_seconds, bool) or not isinstance(max_ttl_seconds, int)
                or not 1 <= max_ttl_seconds <= 3600):
            raise ValueError("invalid_max_ttl")
        if not callable(getattr(principal_registry, "with_trusted_principal", None)):
            raise TypeError("principal_registry_transaction_required")
        self._secret = bytes(secret)
        self.database_path = str(Path(raw_path))
        self._registry = principal_registry
        self._clock = clock
        self._max_ttl = max_ttl_seconds
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS principal_action_grants ("
                "nonce_hash TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "principal_key_fingerprint TEXT NOT NULL, action_fingerprint TEXT NOT NULL, "
                "execution_id TEXT NOT NULL, expires_at INTEGER NOT NULL, "
                "signature TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0 "
                "CHECK(consumed IN (0,1)))"
            )
        finally:
            connection.close()
        try:
            os.chmod(self.database_path, 0o600)
        except OSError as exc:
            raise RuntimeError("grant_database_permissions_unavailable") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _fingerprint(identity: PrincipalIdentity) -> str:
        if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_principal_identity")
        return hashlib.sha256(identity.public_key).hexdigest()

    @staticmethod
    def _nonce_hash(nonce: bytes) -> str:
        return hashlib.sha256(nonce).hexdigest()

    @staticmethod
    def _action_fingerprint(action: ActionSpec) -> str:
        return AuthorizationAuthority._action_fingerprint(action)

    def _signature(
        self, principal_id: str, key_fingerprint: str, action_fingerprint: str,
        execution_id: str, nonce: bytes, expires_at: int,
    ) -> str:
        import json
        payload = json.dumps(
            {
                "principal_id": principal_id,
                "principal_key_fingerprint": key_fingerprint,
                "action_fingerprint": action_fingerprint,
                "execution_id": execution_id,
                "nonce": nonce.hex(),
                "expires_at": expires_at,
            },
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        return hmac.new(self._secret, b"NORYX7/PRINCIPAL_ACTION_GRANT/v1\\x00" + payload,
                        hashlib.sha256).hexdigest()

    def issue(
        self, action: ActionSpec, execution_id: str, principal_id: str, *,
        ttl_seconds: int = 60,
    ) -> PrincipalAuthorizationGrant:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("invalid_action")
        if not action.requires_authorization:
            raise ValueError("action_authorization_not_required")
        if (not isinstance(execution_id, str) or not execution_id.strip()
                or len(execution_id.encode("utf-8")) > 256
                or action.execution_id != execution_id):
            raise ValueError("execution_identity_mismatch")
        if (isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int)
                or not 1 <= ttl_seconds <= self._max_ttl):
            raise ValueError("invalid_grant_ttl")
        now = self._clock()
        if isinstance(now, bool) or not isinstance(now, int) or now < 0:
            raise RuntimeError("trusted_clock_unavailable")
        action_fp = self._action_fingerprint(action)

        def create(identity: PrincipalIdentity) -> PrincipalAuthorizationGrant:
            key_fp = self._fingerprint(identity)
            nonce = secrets.token_bytes(32)
            expires_at = now + ttl_seconds
            signature = self._signature(
                identity.principal_id, key_fp, action_fp, execution_id, nonce, expires_at
            )
            grant = PrincipalAuthorizationGrant(
                identity.principal_id, key_fp, action_fp, execution_id,
                nonce, expires_at, signature,
            )
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO principal_action_grants "
                    "(nonce_hash, principal_id, principal_key_fingerprint, action_fingerprint, "
                    "execution_id, expires_at, signature, consumed) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                    (self._nonce_hash(nonce), identity.principal_id, key_fp, action_fp,
                     execution_id, expires_at, signature),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()
            return grant

        return self._registry.with_trusted_principal(principal_id, create)

    def consume_and_execute(
        self, action: ActionSpec, execution_id: str,
        grant: PrincipalAuthorizationGrant, executor: Callable[[], object],
    ) -> tuple[bool, object | None]:
        if not callable(executor) or not isinstance(grant, PrincipalAuthorizationGrant):
            return False, None
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return False, None
        if (not isinstance(execution_id, str) or not execution_id.strip()
                or action.execution_id != execution_id
                or grant.execution_id != execution_id
                or not isinstance(grant.principal_id, str) or not grant.principal_id.strip()
                or not isinstance(grant.nonce, bytes) or len(grant.nonce) != 32):
            return False, None
        try:
            now = self._clock()
            if isinstance(now, bool) or not isinstance(now, int) or now < 0:
                return False, None
            if grant.expires_at <= now:
                return False, None
            action_fp = self._action_fingerprint(action)
            if not hmac.compare_digest(action_fp, grant.action_fingerprint):
                return False, None
            expected = self._signature(
                grant.principal_id, grant.principal_key_fingerprint,
                grant.action_fingerprint, grant.execution_id, grant.nonce, grant.expires_at,
            )
            if not hmac.compare_digest(expected, grant.signature):
                return False, None

            def dispatch(identity: PrincipalIdentity):
                key_fp = self._fingerprint(identity)
                if not hmac.compare_digest(key_fp, grant.principal_key_fingerprint):
                    raise PermissionError("principal_key_changed")
                connection = self._connect()
                try:
                    connection.execute("BEGIN IMMEDIATE")
                    cursor = connection.execute(
                        "UPDATE principal_action_grants SET consumed=1 "
                        "WHERE nonce_hash=? AND principal_id=? AND principal_key_fingerprint=? "
                        "AND action_fingerprint=? AND execution_id=? AND expires_at=? "
                        "AND signature=? AND consumed=0 AND expires_at>?",
                        (self._nonce_hash(grant.nonce), grant.principal_id,
                         grant.principal_key_fingerprint, grant.action_fingerprint,
                         grant.execution_id, grant.expires_at, grant.signature, now),
                    )
                    if cursor.rowcount != 1:
                        connection.execute("ROLLBACK")
                        raise PermissionError("grant_invalid_or_already_consumed")
                    connection.execute("COMMIT")
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
                finally:
                    connection.close()
                return executor()

            result = self._registry.with_trusted_principal(grant.principal_id, dispatch)
            return True, result
        except (PermissionError, ValueError, TypeError, sqlite3.Error, OSError):
            return False, None
