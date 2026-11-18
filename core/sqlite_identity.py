import os
import sqlite3
from pathlib import Path
from typing import Callable, TypeVar

from .identity import AgentIdentity, IdentityRegistry, MAX_ID_SIZE

T = TypeVar("T")


class SQLiteIdentityRegistry(IdentityRegistry):
    """Durable trust-anchor registry with permanent revocation tombstones."""

    _SCHEMA_VERSION = 2

    def __init__(self, database_path: str | os.PathLike[str]):
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("persistent_identity_database_required")
        raw_path = os.fspath(database_path)
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path == ":memory:":
            raise ValueError("persistent_identity_database_required")
        self.database_path = str(Path(raw_path))
        super().__init__()
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS noryx7_identity_metadata "
                    "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS noryx7_trusted_agents "
                    "(agent_id TEXT PRIMARY KEY, public_key BLOB NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS noryx7_revoked_agents "
                    "(agent_id TEXT PRIMARY KEY, revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
                row = connection.execute(
                    "SELECT value FROM noryx7_identity_metadata WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO noryx7_identity_metadata(key, value) VALUES('schema_version', ?)",
                        (str(self._SCHEMA_VERSION),),
                    )
                elif row[0] == "1":
                    connection.execute(
                        "UPDATE noryx7_identity_metadata SET value = ? WHERE key = 'schema_version'",
                        (str(self._SCHEMA_VERSION),),
                    )
                elif row[0] != str(self._SCHEMA_VERSION):
                    raise ValueError("identity_schema_version_mismatch")
                connection.commit()
                try:
                    os.chmod(self.database_path, 0o600)
                except OSError as exc:
                    raise RuntimeError("identity_database_permissions_unavailable") from exc
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _validate_identity(identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")

    @staticmethod
    def _validate_agent_id(agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        try:
            size = len(agent_id.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_agent_id") from exc
        if size > MAX_ID_SIZE:
            raise ValueError("invalid_agent_id")

    def is_registered(self, agent_id: str) -> bool:
        try:
            self._validate_agent_id(agent_id)
        except ValueError:
            return False
        with self._lock:
            connection = self._connect()
            try:
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_agents WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if revoked is not None:
                    return False
                row = connection.execute(
                    "SELECT 1 FROM noryx7_trusted_agents WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                return row is not None
            except sqlite3.Error:
                return False
            finally:
                connection.close()

    def register(self, identity: AgentIdentity) -> None:
        self._validate_identity(identity)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_agents WHERE agent_id = ?",
                    (identity.agent_id,),
                ).fetchone()
                if revoked is not None:
                    raise PermissionError("agent_identity_permanently_revoked")
                try:
                    connection.execute(
                        "INSERT INTO noryx7_trusted_agents(agent_id, public_key) VALUES(?, ?)",
                        (identity.agent_id, sqlite3.Binary(identity.public_key)),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ValueError("agent_identity_already_registered") from exc
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def revoke(self, agent_id: str) -> None:
        self._validate_agent_id(agent_id)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT OR IGNORE INTO noryx7_revoked_agents(agent_id) VALUES(?)",
                    (agent_id,),
                )
                connection.execute(
                    "DELETE FROM noryx7_trusted_agents WHERE agent_id = ?", (agent_id,)
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            connection = self._connect()
            try:
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_agents WHERE agent_id = ?",
                    (identity.agent_id,),
                ).fetchone()
                if revoked is not None:
                    return False
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_agents WHERE agent_id = ?",
                    (identity.agent_id,),
                ).fetchone()
                if row is None:
                    return False
                stored_identity = AgentIdentity(identity.agent_id, bytes(row[0]))
                return stored_identity.is_well_formed() and stored_identity.public_key == identity.public_key
            except sqlite3.Error:
                return False
            finally:
                connection.close()

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        self._validate_agent_id(agent_id)
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                revoked = connection.execute(
                    "SELECT 1 FROM noryx7_revoked_agents WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if revoked is not None:
                    raise PermissionError("agent_identity_permanently_revoked")
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_agents WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if row is None:
                    raise PermissionError("agent_identity_not_trusted")
                trusted_identity = AgentIdentity(agent_id, bytes(row[0]))
                if not trusted_identity.is_well_formed():
                    raise PermissionError("agent_identity_not_trusted")
                result = callback(trusted_identity)
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
