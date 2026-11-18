"""Crash-persistent principal trust registry with irreversible revocation tombstones."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Callable, TypeVar

from .principal_identity import (
    MAX_PRINCIPAL_ID_SIZE,
    PrincipalIdentity,
    PrincipalIdentityRegistry,
)

T = TypeVar("T")


class SQLitePrincipalIdentityRegistry(PrincipalIdentityRegistry):
    """Durable principal-to-public-key registry.

    This is a trust store, not an identity provider. Only a trusted
    provisioning path should call register(). Revocation tombstones survive
    restart and prevent re-registration of the same principal ID.
    """

    _SCHEMA_VERSION = 1

    def __init__(self, database_path: str | os.PathLike[str]) -> None:
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("persistent_principal_database_required")
        raw_path = os.fspath(database_path)
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path == ":memory:":
            raise ValueError("persistent_principal_database_required")
        self.database_path = str(Path(raw_path))
        super().__init__()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_principal_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_trusted_principals "
                "(principal_id TEXT PRIMARY KEY, public_key BLOB NOT NULL CHECK(length(public_key)=32))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_revoked_principals "
                "(principal_id TEXT PRIMARY KEY, revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            row = connection.execute(
                "SELECT value FROM noryx7_principal_metadata WHERE key='schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO noryx7_principal_metadata(key, value) VALUES('schema_version', ?)",
                    (str(self._SCHEMA_VERSION),),
                )
            elif row[0] != str(self._SCHEMA_VERSION):
                raise ValueError("principal_identity_schema_version_mismatch")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            connection.close()
            raise
        connection.close()
        try:
            os.chmod(self.database_path, 0o600)
        except OSError as exc:
            raise RuntimeError("principal_database_permissions_unavailable") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path, timeout=30, isolation_level=None, check_same_thread=False
        )
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _validate_principal_id(principal_id: str) -> None:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("invalid_principal_id")
        try:
            size = len(principal_id.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_principal_id") from exc
        if size > MAX_PRINCIPAL_ID_SIZE:
            raise ValueError("invalid_principal_id")

    def register(self, identity: PrincipalIdentity) -> None:
        if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_principal_identity")
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_principals WHERE principal_id=?",
                    (identity.principal_id,),
                ).fetchone()
                if revoked is not None:
                    raise PermissionError("principal_identity_permanently_revoked")
                try:
                    connection.execute(
                        "INSERT INTO noryx7_trusted_principals(principal_id, public_key) VALUES(?, ?)",
                        (identity.principal_id, sqlite3.Binary(identity.public_key)),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError("principal_identity_already_registered") from exc
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()

    def revoke(self, principal_id: str) -> None:
        self._validate_principal_id(principal_id)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT OR IGNORE INTO noryx7_revoked_principals(principal_id) VALUES(?)",
                    (principal_id,),
                )
                connection.execute(
                    "DELETE FROM noryx7_trusted_principals WHERE principal_id=?",
                    (principal_id,),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()

    def is_revoked(self, principal_id: str) -> bool:
        try:
            self._validate_principal_id(principal_id)
        except ValueError:
            return True
        with self._lock:
            connection = self._connect()
            try:
                return connection.execute(
                    "SELECT 1 FROM noryx7_revoked_principals WHERE principal_id=?",
                    (principal_id,),
                ).fetchone() is not None
            except sqlite3.Error:
                return True
            finally:
                connection.close()

    def is_trusted(self, identity: PrincipalIdentity) -> bool:
        if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            connection = self._connect()
            try:
                if connection.execute(
                    "SELECT 1 FROM noryx7_revoked_principals WHERE principal_id=?",
                    (identity.principal_id,),
                ).fetchone() is not None:
                    return False
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_principals WHERE principal_id=?",
                    (identity.principal_id,),
                ).fetchone()
                return row is not None and bytes(row[0]) == identity.public_key
            except sqlite3.Error:
                return False
            finally:
                connection.close()

    def with_trusted_principal(
        self, principal_id: str, callback: Callable[[PrincipalIdentity], T]
    ) -> T:
        self._validate_principal_id(principal_id)
        if not callable(callback):
            raise TypeError("callback_must_be_callable")
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                if connection.execute(
                    "SELECT 1 FROM noryx7_revoked_principals WHERE principal_id=?",
                    (principal_id,),
                ).fetchone() is not None:
                    raise PermissionError("principal_identity_permanently_revoked")
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_principals WHERE principal_id=?",
                    (principal_id,),
                ).fetchone()
                if row is None:
                    raise PermissionError("principal_identity_not_trusted")
                identity = PrincipalIdentity(principal_id, bytes(row[0]))
                if not identity.is_well_formed():
                    raise PermissionError("principal_identity_not_trusted")
                result = callback(identity)
                connection.execute("COMMIT")
                return result
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()
