"""Keyed journal-record integrity primitives and an external anti-rollback contract.

This module does not store journal data or manage production keys. The caller must
obtain the key from an external KMS/HSM and anchor the head outside the journal DB.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import math
from typing import Protocol, Iterable

ZERO_MAC = "0" * 64


def _hex_digest(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class JournalRecordProof:
    sequence: int
    previous_mac: str
    payload_digest: str
    key_id: str
    mac: str


@dataclass(frozen=True)
class AnchorSnapshot:
    sequence: int
    mac: str


class MonotonicAnchor(Protocol):
    """Must be implemented by storage outside the journal's rollback domain."""

    def read(self) -> AnchorSnapshot: ...
    def compare_and_swap(self, expected: AnchorSnapshot, replacement: AnchorSnapshot) -> bool: ...


class JournalAuthenticator:
    """HMAC-SHA256 record-chain authenticator; key bytes must come from a KMS/HSM."""

    def __init__(self, key: bytes, *, key_id: str) -> None:
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("journal_integrity_key_too_short")
        if not isinstance(key_id, str) or not key_id.strip() or len(key_id) > 128:
            raise ValueError("invalid_journal_key_id")
        self._key = bytes(key)
        self.key_id = key_id

    @staticmethod
    def payload_digest(payload: bytes) -> str:
        if not isinstance(payload, bytes):
            raise TypeError("journal_payload_must_be_bytes")
        return hashlib.sha256(payload).hexdigest()

    def _mac(self, sequence: int, previous_mac: str, payload_digest: str) -> str:
        statement = {
            "domain": "NORYX7_STATE_JOURNAL_V1",
            "sequence": sequence,
            "previous_mac": previous_mac,
            "payload_digest": payload_digest,
            "key_id": self.key_id,
        }
        encoded = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._key, encoded, hashlib.sha256).hexdigest()

    def create(self, sequence: int, previous_mac: str, payload: bytes) -> JournalRecordProof:
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise ValueError("invalid_journal_sequence")
        if not _hex_digest(previous_mac):
            raise ValueError("invalid_previous_journal_mac")
        digest = self.payload_digest(payload)
        return JournalRecordProof(sequence, previous_mac, digest, self.key_id,
                                  self._mac(sequence, previous_mac, digest))

    def verify(self, proof: JournalRecordProof, payload: bytes) -> bool:
        if not isinstance(proof, JournalRecordProof):
            return False
        if isinstance(proof.sequence, bool) or not isinstance(proof.sequence, int) or proof.sequence < 1:
            return False
        if proof.key_id != self.key_id or not _hex_digest(proof.previous_mac):
            return False
        if not _hex_digest(proof.payload_digest) or not _hex_digest(proof.mac):
            return False
        try:
            digest = self.payload_digest(payload)
        except (TypeError, ValueError):
            return False
        if not hmac.compare_digest(digest, proof.payload_digest):
            return False
        expected = self._mac(proof.sequence, proof.previous_mac, digest)
        return hmac.compare_digest(expected, proof.mac)

    def verify_chain(self, entries: Iterable[tuple[JournalRecordProof, bytes]]) -> AnchorSnapshot:
        expected_sequence = 1
        previous_mac = ZERO_MAC
        head = AnchorSnapshot(0, ZERO_MAC)
        for proof, payload in entries:
            if not isinstance(proof, JournalRecordProof):
                raise ValueError("invalid_journal_proof")
            if proof.sequence != expected_sequence or proof.previous_mac != previous_mac:
                raise ValueError("journal_chain_discontinuity")
            if not self.verify(proof, payload):
                raise ValueError("journal_record_authentication_failure")
            previous_mac = proof.mac
            head = AnchorSnapshot(expected_sequence, previous_mac)
            expected_sequence += 1
        return head


def verify_anchored_head(authenticator: JournalAuthenticator,
                         entries: Iterable[tuple[JournalRecordProof, bytes]],
                         anchor: MonotonicAnchor) -> AnchorSnapshot:
    """Rejects a journal whose verified head differs from its external monotonic anchor."""
    if not callable(getattr(anchor, "read", None)):
        raise TypeError("monotonic_anchor_read_required")
    head = authenticator.verify_chain(entries)
    anchored = anchor.read()
    if not isinstance(anchored, AnchorSnapshot):
        raise ValueError("invalid_monotonic_anchor_snapshot")
    if anchored != head:
        raise ValueError("journal_anchor_mismatch")
    return head


class InMemoryMonotonicAnchor:
    """Test-only anchor. It is not rollback-resistant across process or host compromise."""

    def __init__(self) -> None:
        self._snapshot = AnchorSnapshot(0, ZERO_MAC)

    def read(self) -> AnchorSnapshot:
        return self._snapshot

    def compare_and_swap(self, expected: AnchorSnapshot, replacement: AnchorSnapshot) -> bool:
        if not isinstance(expected, AnchorSnapshot) or not isinstance(replacement, AnchorSnapshot):
            return False
        if replacement.sequence != expected.sequence + 1 or not _hex_digest(replacement.mac):
            return False
        if self._snapshot != expected:
            return False
        self._snapshot = replacement
        return True
