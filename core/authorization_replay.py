"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import sqlite3
import threading
import math
import time
import os
import hashlib
import hmac
import json

MAX_TOKENS = 1_000_000
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes authorization tokens once; persistent mode survives process restarts.

    In-memory mode is intended for tests and non-privileged development only.
    High-risk RuntimeEngine actions require a file-backed SQLite guard.
    """

    SCHEMA_VERSION = 2

    def __init__(self, *, max_tokens: int = MAX_TOKENS, path: str | None = None) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ValueError("invalid_replay_guard_path")
        self._max_tokens = max_tokens
        self._path = path
        self._consumed: dict[bytes, float] = {}
        self._lock = threading.RLock()
        self._db: sqlite3.Connection | None = None
        self._closed = False
        if path is not None and path != ":memory:":
            if not os.path.isabs(path):
                raise ValueError("absolute_replay_guard_path_required")
            if os.path.islink(path):
                raise ValueError("replay_guard_symlink_path_rejected")
            db = sqlite3.connect(
                path,
                timeout=30,
                isolation_level=None,
                check_same_thread=False,
            )
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=FULL")
                db.execute("PRAGMA busy_timeout=30000")
                db.execute("PRAGMA trusted_schema=OFF")
                db.execute("PRAGMA secure_delete=ON")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS replay_guard_tokens ("
                    "token BLOB PRIMARY KEY, expires_at REAL NOT NULL) WITHOUT ROWID"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS replay_guard_meta ("
                    "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                row = db.execute(
                    "SELECT value FROM replay_guard_meta WHERE key='max_tokens'"
                ).fetchone()
                if row is None:
                    db.execute(
                        "INSERT INTO replay_guard_meta(key,value) VALUES('max_tokens',?)",
                        (str(max_tokens),),
                    )
                    db.execute(
                        "INSERT INTO replay_guard_meta(key,value) VALUES('schema_version',?)",
                        (str(self.SCHEMA_VERSION),),
                    )
                elif row[0] != str(max_tokens):
                    raise ValueError("replay_guard_capacity_mismatch")
                schema = db.execute(
                    "SELECT value FROM replay_guard_meta WHERE key='schema_version'"
                ).fetchone()
                if schema is None or schema[0] != str(self.SCHEMA_VERSION):
                    raise ValueError("unsupported_replay_guard_schema")
            except Exception:
                db.close()
                raise
            try:
                if os.name == "posix":
                    os.chmod(path, 0o600)
            except OSError:
                db.close()
                raise
            self._db = db

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def durable(self) -> bool:
        return self._db is not None and not self._closed

    @property
    def integrity_protected(self) -> bool:
        return False

    @property
    def consumed_count(self) -> int:
        with self._lock:
            if self._closed:
                raise RuntimeError("replay_guard_closed")
            if self._db is None:
                return len(self._consumed)
            try:
                return int(self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_tokens"
                ).fetchone()[0])
            except sqlite3.Error as exc:
                raise RuntimeError("replay_guard_storage_unavailable") from exc

    def consume(self, token: bytes, *, expires_at: float, now: float | None = None) -> bool:
        """Atomically consume a token until expiry; expired rows are reclaimed safely."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in (expires_at, now)) or expires_at <= now:
            return False
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                self._consumed = {key: expiry for key, expiry in self._consumed.items() if expiry > now}
                if token in self._consumed or len(self._consumed) >= self._max_tokens:
                    return False
                self._consumed[bytes(token)] = float(expires_at)
                return True
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute("DELETE FROM replay_guard_tokens WHERE expires_at<=?", (float(now),))
                exists = self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=? AND expires_at>?",
                    (sqlite3.Binary(token), float(now)),
                ).fetchone()
                if exists is not None:
                    self._db.execute("COMMIT")
                    return False
                count = self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_tokens"
                ).fetchone()[0]
                if count >= self._max_tokens:
                    self._db.execute("ROLLBACK")
                    return False
                self._db.execute(
                    "INSERT INTO replay_guard_tokens(token,expires_at) VALUES(?,?)",
                    (sqlite3.Binary(token), float(expires_at)),
                )
                self._db.execute("COMMIT")
                return True
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def contains(self, token: bytes, *, now: float | None = None) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(float(now)):
            return True
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                expiry = self._consumed.get(token)
                if expiry is None:
                    return False
                if expiry <= now:
                    self._consumed.pop(token, None)
                    return False
                return True
            try:
                return self._db.execute(
                    "SELECT 1 FROM replay_guard_tokens WHERE token=? AND expires_at>?",
                    (sqlite3.Binary(token), float(now)),
                ).fetchone() is not None
            except sqlite3.Error:
                return False

    def consume_many(
        self, tokens: tuple[bytes, ...], *, expires_at: float, now: float | None = None
    ) -> bool:
        """Atomically consume a bounded batch or consume none of it."""
        if (
            not isinstance(tokens, tuple) or not tokens or len(tokens) > 256
            or any(not isinstance(token, bytes) or len(token) != TOKEN_SIZE for token in tokens)
            or len(set(tokens)) != len(tokens)
        ):
            return False
        now = time.time() if now is None else now
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (expires_at, now)
        ) or expires_at <= now:
            return False
        with self._lock:
            if self._closed:
                return False
            if self._db is None:
                self._consumed = {
                    key: expiry for key, expiry in self._consumed.items() if expiry > now
                }
                if any(token in self._consumed for token in tokens):
                    return False
                if len(self._consumed) + len(tokens) > self._max_tokens:
                    return False
                for token in tokens:
                    self._consumed[bytes(token)] = float(expires_at)
                return True
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "DELETE FROM replay_guard_tokens WHERE expires_at<=?", (float(now),)
                )
                placeholders = ",".join("?" for _ in tokens)
                existing = self._db.execute(
                    f"SELECT 1 FROM replay_guard_tokens WHERE token IN ({placeholders}) LIMIT 1",
                    tuple(sqlite3.Binary(token) for token in tokens),
                ).fetchone()
                if existing is not None:
                    self._db.execute("ROLLBACK")
                    return False
                count = self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_tokens"
                ).fetchone()[0]
                if count + len(tokens) > self._max_tokens:
                    self._db.execute("ROLLBACK")
                    return False
                self._db.executemany(
                    "INSERT INTO replay_guard_tokens(token,expires_at) VALUES(?,?)",
                    [(sqlite3.Binary(token), float(expires_at)) for token in tokens],
                )
                self._db.execute("COMMIT")
                return True
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            self._closed = True


class AuthenticatedAuthorizationReplayGuard(AuthorizationReplayGuard):
    """File-backed replay guard with keyed token fingerprints and authenticated rows.

    The HMAC key is externally provisioned. This detects row modification and
    expiry tampering, but cannot detect deletion or rollback of the entire DB
    without an external monotonic witness.
    """

    AUTH_SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        integrity_key: bytes,
        key_id: str,
        max_tokens: int = MAX_TOKENS,
        path: str,
    ) -> None:
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("replay_guard_integrity_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("invalid_replay_guard_key_id")
        if not isinstance(path, str) or not path.strip() or path == ":memory:":
            raise ValueError("persistent_replay_guard_path_required")
        super().__init__(max_tokens=max_tokens, path=path)
        if self._db is None:
            raise RuntimeError("persistent_replay_guard_unavailable")
        legacy_count = self._db.execute(
            "SELECT COUNT(*) FROM replay_guard_tokens"
        ).fetchone()[0]
        if legacy_count:
            self.close()
            raise RuntimeError("legacy_replay_tokens_require_explicit_migration")
        self._integrity_key = bytes(integrity_key)
        self._integrity_key_id = key_id
        try:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS replay_guard_auth_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS replay_guard_auth_tokens ("
                "token_hash BLOB PRIMARY KEY, expires_at REAL NOT NULL, "
                "key_id TEXT NOT NULL, record_mac BLOB NOT NULL) WITHOUT ROWID"
            )
            rows = dict(self._db.execute(
                "SELECT key,value FROM replay_guard_auth_meta"
            ).fetchall())
            if not rows:
                self._db.execute("BEGIN IMMEDIATE")
                try:
                    self._db.execute(
                        "INSERT INTO replay_guard_auth_meta(key,value) VALUES('schema_version',?)",
                        (str(self.AUTH_SCHEMA_VERSION),),
                    )
                    self._db.execute(
                        "INSERT INTO replay_guard_auth_meta(key,value) VALUES('key_id',?)",
                        (self._integrity_key_id,),
                    )
                    self._db.execute(
                        "INSERT INTO replay_guard_auth_meta(key,value) VALUES('max_tokens',?)",
                        (str(max_tokens),),
                    )
                    self._db.execute("COMMIT")
                except Exception:
                    if self._db.in_transaction:
                        self._db.execute("ROLLBACK")
                    raise
            elif (
                rows.get("schema_version") != str(self.AUTH_SCHEMA_VERSION)
                or rows.get("key_id") != self._integrity_key_id
                or rows.get("max_tokens") != str(max_tokens)
            ):
                raise RuntimeError("authenticated_replay_guard_metadata_mismatch")
            self._verify_all_rows()
        except Exception:
            self.close()
            raise

    @property
    def authenticated(self) -> bool:
        return self._db is not None and not self._closed

    @property
    def integrity_protected(self) -> bool:
        return self.authenticated

    def _token_hash(self, token: bytes) -> bytes:
        return hmac.new(
            self._integrity_key,
            b"NORYX7_AUTH_REPLAY_TOKEN_V1\x00" + token,
            hashlib.sha256,
        ).digest()

    def _record_mac(self, token_hash: bytes, expires_at: float, key_id: str) -> bytes:
        statement = json.dumps(
            {
                "domain": "NORYX7_AUTH_REPLAY_RECORD_V1",
                "token_hash": token_hash.hex(),
                "expires_at": float(expires_at).hex(),
                "key_id": key_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hmac.new(self._integrity_key, statement, hashlib.sha256).digest()

    def _verify_row(self, row) -> bool:
        token_hash, expires_at, key_id, record_mac = row
        if (
            not isinstance(token_hash, bytes) or len(token_hash) != 32
            or isinstance(expires_at, bool) or not isinstance(expires_at, (int, float))
            or not math.isfinite(float(expires_at))
            or key_id != self._integrity_key_id
            or not isinstance(record_mac, bytes) or len(record_mac) != 32
        ):
            return False
        expected = self._record_mac(token_hash, float(expires_at), key_id)
        return hmac.compare_digest(expected, record_mac)

    def _verify_all_rows(self) -> None:
        rows = self._db.execute(
            "SELECT token_hash,expires_at,key_id,record_mac FROM replay_guard_auth_tokens"
        ).fetchall()
        if len(rows) > self._max_tokens or any(not self._verify_row(row) for row in rows):
            raise RuntimeError("authenticated_replay_guard_integrity_failure")

    def _fail_integrity(self) -> None:
        self._closed = True
        raise RuntimeError("authenticated_replay_guard_integrity_failure")

    @property
    def consumed_count(self) -> int:
        with self._lock:
            if self._closed or self._db is None:
                raise RuntimeError("replay_guard_closed")
            try:
                return int(self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_auth_tokens"
                ).fetchone()[0])
            except sqlite3.Error as exc:
                raise RuntimeError("replay_guard_storage_unavailable") from exc

    def consume(self, token: bytes, *, expires_at: float, now: float | None = None) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (expires_at, now)
        ) or expires_at <= now:
            return False
        with self._lock:
            if self._closed or self._db is None:
                return False
            token_hash = self._token_hash(token)
            try:
                self._db.execute("BEGIN IMMEDIATE")
                expired_rows = self._db.execute(
                    "SELECT token_hash,expires_at,key_id,record_mac "
                    "FROM replay_guard_auth_tokens WHERE expires_at<=?",
                    (float(now),),
                ).fetchall()
                if any(not self._verify_row(row) for row in expired_rows):
                    self._db.execute("ROLLBACK")
                    self._fail_integrity()
                self._db.execute(
                    "DELETE FROM replay_guard_auth_tokens WHERE expires_at<=?",
                    (float(now),),
                )
                existing = self._db.execute(
                    "SELECT token_hash,expires_at,key_id,record_mac "
                    "FROM replay_guard_auth_tokens WHERE token_hash=?",
                    (sqlite3.Binary(token_hash),),
                ).fetchone()
                if existing is not None:
                    if not self._verify_row(existing):
                        self._db.execute("ROLLBACK")
                        self._fail_integrity()
                    self._db.execute("ROLLBACK")
                    return False
                count = self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_auth_tokens"
                ).fetchone()[0]
                if count >= self._max_tokens:
                    self._db.execute("ROLLBACK")
                    return False
                expiry = float(expires_at)
                self._db.execute(
                    "INSERT INTO replay_guard_auth_tokens(token_hash,expires_at,key_id,record_mac) "
                    "VALUES(?,?,?,?)",
                    (
                        sqlite3.Binary(token_hash),
                        expiry,
                        self._integrity_key_id,
                        sqlite3.Binary(self._record_mac(token_hash, expiry, self._integrity_key_id)),
                    ),
                )
                self._db.execute("COMMIT")
                return True
            except RuntimeError:
                raise
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def consume_many(
        self, tokens: tuple[bytes, ...], *, expires_at: float, now: float | None = None
    ) -> bool:
        """Atomically consume authenticated token fingerprints as one batch."""
        if (
            not isinstance(tokens, tuple) or not tokens or len(tokens) > 256
            or any(not isinstance(token, bytes) or len(token) != TOKEN_SIZE for token in tokens)
            or len(set(tokens)) != len(tokens)
        ):
            return False
        now = time.time() if now is None else now
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (expires_at, now)
        ) or expires_at <= now:
            return False
        with self._lock:
            if self._closed or self._db is None:
                return False
            token_hashes = tuple(self._token_hash(token) for token in tokens)
            try:
                self._db.execute("BEGIN IMMEDIATE")
                expired_rows = self._db.execute(
                    "SELECT token_hash,expires_at,key_id,record_mac "
                    "FROM replay_guard_auth_tokens WHERE expires_at<=?",
                    (float(now),),
                ).fetchall()
                if any(not self._verify_row(row) for row in expired_rows):
                    self._db.execute("ROLLBACK")
                    self._fail_integrity()
                self._db.execute(
                    "DELETE FROM replay_guard_auth_tokens WHERE expires_at<=?",
                    (float(now),),
                )
                placeholders = ",".join("?" for _ in token_hashes)
                existing_rows = self._db.execute(
                    "SELECT token_hash,expires_at,key_id,record_mac "
                    f"FROM replay_guard_auth_tokens WHERE token_hash IN ({placeholders})",
                    tuple(sqlite3.Binary(value) for value in token_hashes),
                ).fetchall()
                if any(not self._verify_row(row) for row in existing_rows):
                    self._db.execute("ROLLBACK")
                    self._fail_integrity()
                if existing_rows:
                    self._db.execute("ROLLBACK")
                    return False
                count = self._db.execute(
                    "SELECT COUNT(*) FROM replay_guard_auth_tokens"
                ).fetchone()[0]
                if count + len(token_hashes) > self._max_tokens:
                    self._db.execute("ROLLBACK")
                    return False
                expiry = float(expires_at)
                self._db.executemany(
                    "INSERT INTO replay_guard_auth_tokens(token_hash,expires_at,key_id,record_mac) "
                    "VALUES(?,?,?,?)",
                    [
                        (
                            sqlite3.Binary(token_hash),
                            expiry,
                            self._integrity_key_id,
                            sqlite3.Binary(self._record_mac(
                                token_hash, expiry, self._integrity_key_id
                            )),
                        )
                        for token_hash in token_hashes
                    ],
                )
                self._db.execute("COMMIT")
                return True
            except RuntimeError:
                raise
            except sqlite3.Error:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                return False

    def contains(self, token: bytes, *, now: float | None = None) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        now = time.time() if now is None else now
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(float(now)):
            return True
        with self._lock:
            if self._closed or self._db is None:
                return False
            try:
                row = self._db.execute(
                    "SELECT token_hash,expires_at,key_id,record_mac "
                    "FROM replay_guard_auth_tokens WHERE token_hash=?",
                    (sqlite3.Binary(self._token_hash(token)),),
                ).fetchone()
                if row is None:
                    return False
                if not self._verify_row(row):
                    self._fail_integrity()
                return float(row[1]) > float(now)
            except RuntimeError:
                raise
            except sqlite3.Error:
                return False
