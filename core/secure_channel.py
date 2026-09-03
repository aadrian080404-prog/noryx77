"""Authenticated session framing with strict identity and replay protection."""

from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from typing import Final

from cryptography.hazmat.primitives import hashes, hmac

from .crypto import KEY_SIZE, KeyProvider, derive_subkey


MAC_SIZE: Final[int] = 32
MAX_FRAME_SIZE: Final[int] = 16 * 1024 * 1024
MAX_ID_SIZE: Final[int] = 1024
PROTOCOL_VERSION: Final[int] = 1
MAX_SEQUENCE: Final[int] = (1 << 64) - 1
_DOMAIN: Final[bytes] = b"noryx7/secure-channel/v1/"


def _field(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_ID_SIZE:
        raise ValueError("channel_identity_size_exceeded")
    return len(encoded).to_bytes(4, "big") + encoded


@dataclass(frozen=True)
class SecureFrame:
    """A versioned, authenticated frame carrying one ordered payload."""

    sender_id: str
    session_id: str
    sequence: int
    payload: bytes
    mac: bytes
    version: int = PROTOCOL_VERSION

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.sender_id, str)
            and bool(self.sender_id.strip())
            and len(self.sender_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.session_id, str)
            and bool(self.session_id.strip())
            and len(self.session_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.sequence, int)
            and not isinstance(self.sequence, bool)
            and 0 <= self.sequence <= MAX_SEQUENCE
            and isinstance(self.payload, bytes)
            and len(self.payload) <= MAX_FRAME_SIZE
            and isinstance(self.mac, bytes)
            and len(self.mac) == MAC_SIZE
            and self.version == PROTOCOL_VERSION
        )


class SecureChannel:
    """Symmetric authenticated channel with identity binding and monotonic replay defense."""

    def __init__(
        self,
        provider: KeyProvider,
        *,
        key_id: str,
        local_id: str,
        peer_id: str,
        session_id: str,
        direction: str,
    ):
        if not isinstance(provider, KeyProvider):
            raise ValueError("key_provider_required")
        for name, value in (("key_id", key_id), ("local_id", local_id), ("peer_id", peer_id), ("session_id", session_id), ("direction", direction)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"invalid_{name}")
            if len(value.encode("utf-8")) > MAX_ID_SIZE:
                raise ValueError(f"{name}_size_exceeded")
        if local_id == peer_id:
            raise ValueError("local_and_peer_id_must_differ")
        if direction not in {"send", "receive"}:
            raise ValueError("invalid_direction")
        self._provider = provider
        self._key_id = key_id
        self._local_id = local_id
        self._peer_id = peer_id
        self._session_id = session_id
        self._direction = direction
        self._send_sequence = 0
        self._last_received = -1

    def _channel_key(self) -> bytes:
        try:
            root_key = self._provider.get_key(self._key_id)
        except Exception as exc:
            raise ValueError("channel_key_unavailable") from exc
        if not isinstance(root_key, bytes) or len(root_key) != KEY_SIZE:
            raise ValueError("channel_key_required")
        try:
            return derive_subkey(
                root_key,
                salt=self._session_id.encode("utf-8"),
                context=(b"secure-channel/" + self._direction.encode("ascii")),
            )
        except Exception as exc:
            raise ValueError("channel_key_derivation_failed") from exc

    @staticmethod
    def _encode(version: int, sender_id: str, session_id: str, sequence: int, payload: bytes) -> bytes:
        return (
            _DOMAIN
            + version.to_bytes(2, "big")
            + _field(sender_id)
            + _field(session_id)
            + sequence.to_bytes(8, "big")
            + len(payload).to_bytes(8, "big")
            + payload
        )

    def _mac(self, sender_id: str, sequence: int, payload: bytes) -> bytes:
        signer = hmac.HMAC(self._channel_key(), hashes.SHA256())
        signer.update(self._encode(PROTOCOL_VERSION, sender_id, self._session_id, sequence, payload))
        return signer.finalize()

    def send(self, payload: bytes) -> SecureFrame:
        if not isinstance(payload, bytes):
            raise TypeError("payload_must_be_bytes")
        if len(payload) > MAX_FRAME_SIZE:
            raise ValueError("frame_size_exceeded")
        if self._send_sequence > MAX_SEQUENCE:
            raise ValueError("sequence_exhausted")
        sequence = self._send_sequence
        mac = self._mac(self._local_id, sequence, payload)
        self._send_sequence += 1
        return SecureFrame(self._local_id, self._session_id, sequence, bytes(payload), mac)

    def receive(self, frame: SecureFrame) -> bytes:
        if not isinstance(frame, SecureFrame) or not frame.is_well_formed():
            raise ValueError("invalid_secure_frame")
        if frame.sender_id != self._peer_id or frame.session_id != self._session_id:
            raise ValueError("channel_identity_mismatch")
        if frame.sequence <= self._last_received:
            raise ValueError("replayed_frame")
        try:
            expected = self._mac(frame.sender_id, frame.sequence, frame.payload)
        except Exception as exc:
            raise ValueError("frame_authentication_failed") from exc
        if not compare_digest(expected, frame.mac):
            raise ValueError("frame_authentication_failed")
        self._last_received = frame.sequence
        return bytes(frame.payload)

    @property
    def last_received_sequence(self) -> int:
        return self._last_received
