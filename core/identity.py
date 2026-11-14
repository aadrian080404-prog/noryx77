

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
