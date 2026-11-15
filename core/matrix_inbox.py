"""Durable authenticated inbox reference for the Matrix network fabric.

This is a local SQLite inbox, not a socket transport, PKI, or consensus layer.
The caller supplies the shared key and trusted sender/recipient identities.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
import sqlite3
from contextlib import contextmanager
from typing import Iterator


@dataclass(frozen=True)
class InboxReceipt:
    message_id: str
    sender_id: str
    recipient_id: str
    key_id: str
    payload_digest: str
    expires_at: int
    state: str


def _canonical(sender_id: str, recipient_id: str, message_id: str,
               key_id: str, expires_at: int, payload: bytes) -> bytes:
    fields = (sender_id, recipient_id, message_id, key_id, str(expires_at))
    return b"\x00".join(value.encode("utf-8") for value in fields) + b"\x00" + payload


def sign_message(sender_id: str, recipient_id: str, message_id: str,
                 key_id: str, expires_at: int, payload: bytes, key: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("authentication_key_must_be_at_least_32_bytes")
    return hmac.new(key, _canonical(sender_id, recipient_id, message_id,
                                    key_id, expires_at, payload), hashlib.sha256).hexdigest()


class DurableInbox:
    def __init__(self, database: str, recipient_id: str, trusted_keys: dict[str, bytes],
                 *, max_payload_bytes: int = 1_048_576, timeout: float = 5.0) -> None:
        if not isinstance(database, str) or not database:
            raise ValueError("database_path_required")
        if not isinstance(recipient_id, str) or not recipient_id.strip():
            raise ValueError("recipient_id_required")
        if not isinstance(trusted_keys, dict) or not trusted_keys:
            raise ValueError("trusted_keys_required")
        if isinstance(max_payload_bytes, bool) or not isinstance(max_payload_bytes, int) or max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes_must_be_positive")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout_must_be_finite_and_positive")
        for key_id, key in trusted_keys.items():
            if not isinstance(key_id, str) or not key_id.strip() or not isinstance(key, bytes) or len(key) < 32:
                raise ValueError("invalid_trusted_key")
        self.database = database
        self.recipient_id = recipient_id
        self.trusted_keys = dict(trusted_keys)
        self.max_payload_bytes = max_payload_bytes
        self.timeout = float(timeout)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS matrix_inbox (
                recipient_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                key_id TEXT NOT NULL,
                payload BLOB NOT NULL,
                payload_digest TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','DELIVERED','EXPIRED')),
                PRIMARY KEY(recipient_id, message_id)
            )""")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database, timeout=self.timeout, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=%d" % int(self.timeout * 1000))
            yield db
        finally:
            db.close()

    def accept(self, sender_id: str, recipient_id: str, message_id: str,
               key_id: str, expires_at: int, payload: bytes, signature: str,
               *, now: int) -> InboxReceipt:
        for name, value in (("sender_id", sender_id), ("recipient_id", recipient_id),
                            ("message_id", message_id), ("key_id", key_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name + "_required")
        if recipient_id != self.recipient_id:
            raise PermissionError("message_recipient_mismatch")
        if isinstance(expires_at, bool) or not isinstance(expires_at, int) or expires_at <= 0:
            raise ValueError("expires_at_must_be_positive_integer")
        if isinstance(now, bool) or not isinstance(now, int) or now < 0:
            raise ValueError("now_must_be_nonnegative_integer")
        if not isinstance(payload, bytes) or len(payload) > self.max_payload_bytes:
            raise ValueError("payload_invalid_or_too_large")
        key = self.trusted_keys.get(key_id)
        if key is None:
            raise PermissionError("untrusted_message_key_id")
        expected = sign_message(sender_id, recipient_id, message_id, key_id, expires_at, payload, key)
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise PermissionError("message_authentication_failed")
        if expires_at <= now:
            raise PermissionError("message_expired")
        digest = hashlib.sha256(payload).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT sender_id,key_id,payload_digest,expires_at,state FROM matrix_inbox "
                "WHERE recipient_id=? AND message_id=?",
                (recipient_id, message_id),
            ).fetchone()
            if previous is not None:
                if previous[:4] != (sender_id, key_id, digest, expires_at):
                    db.rollback()
                    raise PermissionError("message_id_payload_conflict")
                db.commit()
                return InboxReceipt(message_id, sender_id, recipient_id, key_id,
                                    digest, expires_at, previous[4])
            db.execute(
                "INSERT INTO matrix_inbox VALUES(?,?,?,?,?,?,?,'PENDING')",
                (recipient_id, message_id, sender_id, key_id, payload, digest, expires_at),
            )
            db.commit()
        return InboxReceipt(message_id, sender_id, recipient_id, key_id,
                            digest, expires_at, "PENDING")

    def mark_delivered(self, message_id: str, *, now: int) -> InboxReceipt:
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError("message_id_required")
        if isinstance(now, bool) or not isinstance(now, int) or now < 0:
            raise ValueError("now_must_be_nonnegative_integer")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT sender_id,key_id,payload_digest,expires_at,state FROM matrix_inbox "
                "WHERE recipient_id=? AND message_id=?",
                (self.recipient_id, message_id),
            ).fetchone()
            if row is None:
                db.rollback()
                raise KeyError("message_not_found")
            if row[3] <= now and row[4] == "PENDING":
                db.execute("UPDATE matrix_inbox SET state='EXPIRED' WHERE recipient_id=? AND message_id=?",
                           (self.recipient_id, message_id))
                db.commit()
                return InboxReceipt(message_id, row[0], self.recipient_id, row[1], row[2], row[3], "EXPIRED")
            if row[4] == "EXPIRED":
                db.rollback()
                raise PermissionError("message_expired")
            if row[4] == "PENDING":
                db.execute("UPDATE matrix_inbox SET state='DELIVERED' WHERE recipient_id=? AND message_id=?",
                           (self.recipient_id, message_id))
            db.commit()
        return InboxReceipt(message_id, row[0], self.recipient_id, row[1], row[2], row[3], "DELIVERED")

    def get(self, message_id: str) -> InboxReceipt | None:
        with self._connection() as db:
            row = db.execute(
                "SELECT sender_id,key_id,payload_digest,expires_at,state FROM matrix_inbox "
                "WHERE recipient_id=? AND message_id=?",
                (self.recipient_id, message_id),
            ).fetchone()
        if row is None:
            return None
        return InboxReceipt(message_id, row[0], self.recipient_id, row[1], row[2], row[3], row[4])
