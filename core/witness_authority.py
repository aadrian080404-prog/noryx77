"""SQLite-backed signing authority for monotonic journal witnesses.

This is the service-side state machine, not an HTTP service or a complete
production deployment. The private signing key must be injected from an
external KMS/HSM. SQLite snapshot rollback remains outside this component's
protection boundary and requires independent monotonic storage/backup controls.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .journal_integrity import AnchorSnapshot, ZERO_MAC
from .remote_witness import SignedWitnessReceipt


_DOMAIN = b"NORYX7/REMOTE_MONOTONIC_WITNESS/v1\x00"


def _valid_mac(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        return len(bytes.fromhex(value)) == 32
    except ValueError:
        return False


class SQLiteWitnessAuthority:
    """Durable, atomic compare-and-swap authority for one witness identity.

    Multiple processes may share the same SQLite database. BEGIN IMMEDIATE
    serializes updates and the sequence/MAC compare is performed in that
    transaction. This does not make restoration of an old database snapshot
    detectable; the witness's own storage rollback domain must be protected
    separately.
    """

    def __init__(
        self,
        path: str,
        *,
        witness_id: str,
        signing_key: Ed25519PrivateKey,
    ) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("witness_database_path_required")
        if not isinstance(witness_id, str) or not witness_id.strip() or len(witness_id) > 128:
            raise ValueError("witness_id_invalid")
        if not isinstance(signing_key, Ed25519PrivateKey):
            raise TypeError("ed25519_private_signing_key_required")
        self.witness_id = witness_id
        self._signing_key = signing_key
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
                "CREATE TABLE IF NOT EXISTS witness_heads ("
                "witness_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL, mac TEXT NOT NULL)"
            )
            self._db.execute(
                "INSERT OR IGNORE INTO witness_heads(witness_id,sequence,mac) VALUES(?,0,?)",
                (self.witness_id, ZERO_MAC),
            )
            self._read_locked()
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("witness_authority_closed")

    def _read_locked(self) -> AnchorSnapshot:
        row = self._db.execute(
            "SELECT sequence,mac FROM witness_heads WHERE witness_id=?",
            (self.witness_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("witness_head_missing")
        sequence, mac = row
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise RuntimeError("witness_sequence_corrupt")
        if not _valid_mac(mac):
            raise RuntimeError("witness_mac_corrupt")
        return AnchorSnapshot(sequence, mac)

    @staticmethod
    def _receipt_message(receipt: SignedWitnessReceipt) -> bytes:
        payload = {
            "witness_id": receipt.witness_id,
            "operation": receipt.operation,
            "nonce": receipt.nonce.hex(),
            "sequence": receipt.snapshot.sequence,
            "mac": receipt.snapshot.mac,
            "accepted": receipt.accepted,
        }
        return _DOMAIN + json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")

    def _make_receipt(
        self, operation: str, nonce: bytes, snapshot: AnchorSnapshot, accepted: bool
    ) -> SignedWitnessReceipt:
        unsigned = SignedWitnessReceipt(
            witness_id=self.witness_id,
            operation=operation,
            nonce=nonce,
            snapshot=snapshot,
            accepted=accepted,
            signature=b"",
        )
        return SignedWitnessReceipt(
            witness_id=unsigned.witness_id,
            operation=unsigned.operation,
            nonce=unsigned.nonce,
            snapshot=unsigned.snapshot,
            accepted=unsigned.accepted,
            signature=self._signing_key.sign(self._receipt_message(unsigned)),
        )

    @staticmethod
    def _validate_nonce(nonce: bytes) -> None:
        if not isinstance(nonce, bytes) or len(nonce) != 32:
            raise ValueError("witness_request_nonce_must_be_32_bytes")

    def read_anchor(self, nonce: bytes) -> SignedWitnessReceipt:
        self._validate_nonce(nonce)
        with self._lock:
            self._ensure_open()
            snapshot = self._read_locked()
            return self._make_receipt("read", nonce, snapshot, True)

    def compare_and_swap_anchor(
        self, expected: AnchorSnapshot, replacement: AnchorSnapshot, nonce: bytes
    ) -> SignedWitnessReceipt:
        self._validate_nonce(nonce)
        if not isinstance(expected, AnchorSnapshot) or not isinstance(replacement, AnchorSnapshot):
            raise TypeError("witness_anchor_snapshots_required")
        if (
            isinstance(expected.sequence, bool)
            or not isinstance(expected.sequence, int)
            or expected.sequence < 0
            or isinstance(replacement.sequence, bool)
            or not isinstance(replacement.sequence, int)
            or replacement.sequence != expected.sequence + 1
            or not _valid_mac(expected.mac)
            or not _valid_mac(replacement.mac)
        ):
            raise ValueError("witness_anchor_transition_invalid")

        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._read_locked()
                accepted = current == expected
                if accepted:
                    self._db.execute(
                        "UPDATE witness_heads SET sequence=?,mac=? WHERE witness_id=?",
                        (replacement.sequence, replacement.mac, self.witness_id),
                    )
                    current = replacement
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
            return self._make_receipt("compare_and_swap", nonce, current, accepted)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True


class InProcessWitnessClient:
    """In-process transport adapter for tests and local integration only."""

    def __init__(self, authority: SQLiteWitnessAuthority) -> None:
        if not isinstance(authority, SQLiteWitnessAuthority):
            raise TypeError("sqlite_witness_authority_required")
        self._authority = authority

    def read_anchor(self, nonce: bytes) -> SignedWitnessReceipt:
        return self._authority.read_anchor(nonce)

    def compare_and_swap_anchor(
        self, expected: AnchorSnapshot, replacement: AnchorSnapshot, nonce: bytes
    ) -> SignedWitnessReceipt:
        return self._authority.compare_and_swap_anchor(expected, replacement, nonce)
