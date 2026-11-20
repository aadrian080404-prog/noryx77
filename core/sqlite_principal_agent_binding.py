"""Durable, fail-closed ownership bindings between principals and agents.

A principal is a user/tenant identity; an agent is an executable identity.
The two registries remain independent. This store records the explicit
provisioning relationship and irreversible relationship-revocation tombstones.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Callable

from core.identity import MAX_ID_SIZE
from core.principal_identity import MAX_PRINCIPAL_ID_SIZE


class SQLitePrincipalAgentBindingRegistry:
    """Durable one-principal-per-agent binding registry.

    Binding is privileged provisioning, not user authentication. Both
    identities must be live in their authoritative trust registries at bind
    time and are rechecked on every ownership query. Revoked bindings cannot
    be recreated; assigning an agent to a different principal requires a new
    agent identity.
    """

    _SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        *,
        principal_registry: object,
        agent_registry: object,
    ) -> None:
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("persistent_binding_database_required")
        raw_path = os.fspath(database_path)
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path == ":memory:":
            raise ValueError("persistent_binding_database_required")
        if not callable(getattr(principal_registry, "with_trusted_principal", None)):
            raise TypeError("durable_principal_trust_registry_required")
        if not callable(getattr(agent_registry, "with_trusted_identity", None)):
            raise TypeError("durable_agent_trust_registry_required")
        self.database_path = str(Path(raw_path))
        self._principal_registry = principal_registry
        self._agent_registry = agent_registry
        self._lock = threading.RLock()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_binding_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_principal_agent_bindings ("
                "agent_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_principal_agent_owner "
                "ON noryx7_principal_agent_bindings(principal_id, agent_id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS noryx7_revoked_principal_agent_bindings ("
                "principal_id TEXT NOT NULL, agent_id TEXT NOT NULL, "
                "revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "PRIMARY KEY(principal_id, agent_id))"
            )
            row = connection.execute(
                "SELECT value FROM noryx7_binding_metadata WHERE key='schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO noryx7_binding_metadata(key, value) VALUES('schema_version', ?)",
                    (str(self._SCHEMA_VERSION),),
                )
            elif row[0] != str(self._SCHEMA_VERSION):
                raise ValueError("principal_agent_binding_schema_version_mismatch")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        try:
            os.chmod(self.database_path, 0o600)
        except OSError as exc:
            raise RuntimeError("binding_database_permissions_unavailable") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path, timeout=30, isolation_level=None, check_same_thread=False
        )
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _validate_ids(principal_id: str, agent_id: str) -> None:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("invalid_principal_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        try:
            principal_size = len(principal_id.encode("utf-8"))
            agent_size = len(agent_id.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_binding_identity") from exc
        if principal_size > MAX_PRINCIPAL_ID_SIZE:
            raise ValueError("invalid_principal_id")
        if agent_size > MAX_ID_SIZE:
            raise ValueError("invalid_agent_id")

    def bind(self, principal_id: str, agent_id: str) -> None:
        """Create a permanent one-owner binding after live identity checks."""
        self._validate_ids(principal_id, agent_id)

        def with_principal(agent_identity):
            if not (
                agent_identity.agent_id == agent_id
                and isinstance(agent_identity.public_key, bytes)
                and len(agent_identity.public_key) == 32
            ):
                return False
            return self._principal_registry.with_trusted_principal(
                principal_id,
                lambda principal_identity: (
                    principal_identity.principal_id == principal_id
                ),
            ) is True

        try:
            # Match ActionGate's global lock order: agent registry, then principal.
            trusted = self._agent_registry.with_trusted_identity(
                agent_id, with_principal
            ) is True
        except Exception as exc:
            raise PermissionError("binding_identity_not_trusted") from exc
        if not trusted:
            raise PermissionError("binding_identity_not_trusted")

        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_principal_agent_bindings "
                    "WHERE principal_id=? AND agent_id=?",
                    (principal_id, agent_id),
                ).fetchone()
                if revoked is not None:
                    raise PermissionError("principal_agent_binding_permanently_revoked")
                owner = connection.execute(
                    "SELECT principal_id FROM noryx7_principal_agent_bindings WHERE agent_id=?",
                    (agent_id,),
                ).fetchone()
                if owner is not None:
                    if owner[0] == principal_id:
                        raise ValueError("principal_agent_binding_already_exists")
                    raise PermissionError("agent_already_bound_to_another_principal")
                connection.execute(
                    "INSERT INTO noryx7_principal_agent_bindings(principal_id, agent_id) "
                    "VALUES(?, ?)",
                    (principal_id, agent_id),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()

    def revoke_binding(self, principal_id: str, agent_id: str) -> None:
        """Revoke one relationship permanently; identity keys are untouched."""
        self._validate_ids(principal_id, agent_id)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT principal_id FROM noryx7_principal_agent_bindings "
                    "WHERE agent_id=?",
                    (agent_id,),
                ).fetchone()
                if row is None or row[0] != principal_id:
                    raise KeyError("principal_agent_binding_not_found")
                connection.execute(
                    "INSERT OR IGNORE INTO noryx7_revoked_principal_agent_bindings"
                    "(principal_id, agent_id) VALUES(?, ?)",
                    (principal_id, agent_id),
                )
                connection.execute(
                    "DELETE FROM noryx7_principal_agent_bindings "
                    "WHERE principal_id=? AND agent_id=?",
                    (principal_id, agent_id),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            finally:
                connection.close()

    def is_agent_owned_by_principal(self, principal_id: str, agent_id: str) -> bool:
        """Return true only for an active binding and two currently trusted IDs."""
        try:
            self._validate_ids(principal_id, agent_id)

            def with_principal(_agent_identity):
                return self._principal_registry.with_trusted_principal(
                    principal_id, lambda _principal_identity: True
                ) is True

            if self._agent_registry.with_trusted_identity(
                agent_id, with_principal
            ) is not True:
                return False
            with self._lock:
                connection = self._connect()
                try:
                    revoked = connection.execute(
                        "SELECT 1 FROM noryx7_revoked_principal_agent_bindings "
                        "WHERE principal_id=? AND agent_id=?",
                        (principal_id, agent_id),
                    ).fetchone()
                    if revoked is not None:
                        return False
                    row = connection.execute(
                        "SELECT 1 FROM noryx7_principal_agent_bindings "
                        "WHERE principal_id=? AND agent_id=?",
                        (principal_id, agent_id),
                    ).fetchone()
                    return row is not None
                finally:
                    connection.close()
        except Exception:
            return False
