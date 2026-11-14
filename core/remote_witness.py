"""Signed client adapter for an external monotonic witness service.

The service/transport is deployment supplied. This module verifies signed,
nonce-bound receipts and never stores witness credentials or private keys.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .journal_integrity import AnchorSnapshot


@dataclass(frozen=True)
class SignedWitnessReceipt:
    witness_id: str
    operation: str
    nonce: bytes
    snapshot: AnchorSnapshot
    accepted: bool
    signature: bytes


class RemoteWitnessClient(Protocol):
    def read_anchor(self, nonce: bytes) -> SignedWitnessReceipt: ...

    def compare_and_swap_anchor(
        self, expected: AnchorSnapshot, replacement: AnchorSnapshot, nonce: bytes
    ) -> SignedWitnessReceipt: ...


class RemoteMonotonicAnchor:
    """Verifies Ed25519-signed, request-nonce-bound witness state receipts."""

    _DOMAIN = b"NORYX7/REMOTE_MONOTONIC_WITNESS/v1\x00"

    def __init__(
        self,
        client: RemoteWitnessClient,
        *,
        witness_id: str,
        trusted_public_key: bytes,
    ) -> None:
        if not callable(getattr(client, "read_anchor", None)) or not callable(
            getattr(client, "compare_and_swap_anchor", None)
        ):
            raise TypeError("remote_witness_client_contract_required")
        if not isinstance(witness_id, str) or not witness_id.strip():
            raise ValueError("witness_id_required")
        if not isinstance(trusted_public_key, bytes) or len(trusted_public_key) != 32:
            raise ValueError("witness_ed25519_public_key_required")
        self._client = client
        self.witness_id = witness_id
        self._public_key = Ed25519PublicKey.from_public_bytes(trusted_public_key)

    @classmethod
    def _message(cls, receipt: SignedWitnessReceipt) -> bytes:
        if not isinstance(receipt.snapshot, AnchorSnapshot):
            raise ValueError("witness_snapshot_required")
        payload = {
            "witness_id": receipt.witness_id,
            "operation": receipt.operation,
            "nonce": receipt.nonce.hex(),
            "sequence": receipt.snapshot.sequence,
            "mac": receipt.snapshot.mac,
            "accepted": receipt.accepted,
        }
        return cls._DOMAIN + json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")

    def _verify(
        self, receipt: SignedWitnessReceipt, *, operation: str, nonce: bytes
    ) -> SignedWitnessReceipt:
        if not isinstance(receipt, SignedWitnessReceipt):
            raise RuntimeError("remote_witness_receipt_invalid")
        if receipt.witness_id != self.witness_id or receipt.operation != operation:
            raise RuntimeError("remote_witness_identity_or_operation_mismatch")
        if not isinstance(receipt.nonce, bytes) or receipt.nonce != nonce:
            raise RuntimeError("remote_witness_nonce_mismatch")
        if not isinstance(receipt.accepted, bool):
            raise RuntimeError("remote_witness_acceptance_flag_invalid")
        if not isinstance(receipt.signature, bytes) or len(receipt.signature) != 64:
            raise RuntimeError("remote_witness_signature_invalid")
        snapshot = receipt.snapshot
        if (
            not isinstance(snapshot, AnchorSnapshot)
            or isinstance(snapshot.sequence, bool)
            or not isinstance(snapshot.sequence, int)
            or snapshot.sequence < 0
            or not isinstance(snapshot.mac, str)
            or len(snapshot.mac) != 64
        ):
            raise RuntimeError("remote_witness_snapshot_invalid")
        try:
            bytes.fromhex(snapshot.mac)
            self._public_key.verify(receipt.signature, self._message(receipt))
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise RuntimeError("remote_witness_signature_verification_failed") from exc
        return receipt

    def read(self) -> AnchorSnapshot:
        import secrets
        nonce = secrets.token_bytes(32)
        receipt = self._verify(
            self._client.read_anchor(nonce), operation="read", nonce=nonce
        )
        if not receipt.accepted:
            raise RuntimeError("remote_witness_read_not_accepted")
        return receipt.snapshot

    def compare_and_swap(
        self, expected: AnchorSnapshot, replacement: AnchorSnapshot
    ) -> bool:
        import secrets
        if not isinstance(expected, AnchorSnapshot) or not isinstance(replacement, AnchorSnapshot):
            return False
        if replacement.sequence != expected.sequence + 1:
            return False
        nonce = secrets.token_bytes(32)
        receipt = self._verify(
            self._client.compare_and_swap_anchor(expected, replacement, nonce),
            operation="compare_and_swap",
            nonce=nonce,
        )
        if receipt.accepted and receipt.snapshot != replacement:
            raise RuntimeError("remote_witness_cas_receipt_mismatch")
        return receipt.accepted
