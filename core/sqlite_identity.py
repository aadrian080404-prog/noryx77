import os
import sqlite3
from pathlib import Path
from typing import Callable, TypeVar

from .identity import AgentIdentity, IdentityRegistry, MAX_ID_SIZE

T = TypeVar("T")


class SQLiteIdentityRegistry(IdentityRegistry):
    """Durable trust-anchor registry shared by processes using one SQLite file."""

    _SCHEMA_VERSION = 1

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
                row = connection.execute(
                    "SELECT value FROM noryx7_identity_metadata WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO noryx7_identity_metadata(key, value) VALUES('schema_version', ?)",
                        (str(self._SCHEMA_VERSION),),
                    )
                elif row[0] != str(self._SCHEMA_VERSION):
                    raise ValueError("identity_schema_version_mismatch")
                connection.commit()
                try:
                    os.chmod(self.database_path, 0o600)
                except OSError:
                    pass
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

    def register(self, identity: AgentIdentity) -> None:
        self._validate_identity(identity)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
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
        if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("invalid_agent_id")
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
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
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_agents WHERE agent_id = ?",
                    (identity.agent_id,),
                ).fetchone()
                return row is not None and bytes(row[0]) == identity.public_key
            except sqlite3.Error:
                return False
            finally:
                connection.close()

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("invalid_agent_id")
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT public_key FROM noryx7_trusted_agents WHERE agent_id = ?",
                    (agent_id,),
                ).fetchone()
                if row is None:
                    raise PermissionError("agent_identity_not_trusted")
                result = callback(AgentIdentity(agent_id, bytes(row[0])))
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
