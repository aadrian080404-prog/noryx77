"""Authenticated session framing with strict cryptographic identity and replay protection."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Final

from cryptography.hazmat.primitives import hashes, hmac

from .crypto import KEY_SIZE, KeyProvider, derive_subkey
from .identity import AgentIdentity, IdentityRegistry

MAC_SIZE: Final[int] = 32
MAX_FRAME_SIZE: Final[int] = 16 * 1024 * 1024
MAX_ID_SIZE: Final[int] = 1024
PROTOCOL_VERSION: Final[int] = 1
MAX_SEQUENCE: Final[int] = (1 << 64) - 1
_DOMAIN: Final[bytes] = b"noryx7/secure-channel/v1/"
_IDENTITY_BINDING_DOMAIN: Final[bytes] = b"noryx7/secure-channel/identity-binding/v1/"


def _field(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_ID_SIZE:
        raise ValueError("channel_identity_size_exceeded")
    return len(encoded).to_bytes(4, "big") + encoded


def _identity_fingerprint(identity: AgentIdentity) -> bytes:
    if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
        raise ValueError("invalid_channel_identity")
    return sha256(
        _IDENTITY_BINDING_DOMAIN
        + identity.version.to_bytes(2, "big")
        + _field(identity.agent_id)
        + identity.public_key
    ).digest()


@dataclass(frozen=True)
class SecureFrame:
    sender_id: str
    session_id: str
    sequence: int
    payload: bytes
    mac: bytes
    version: int = PROTOCOL_VERSION

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.sender_id, str) and bool(self.sender_id.strip()) and len(self.sender_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.session_id, str) and bool(self.session_id.strip()) and len(self.session_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.sequence, int) and not isinstance(self.sequence, bool) and 0 <= self.sequence <= MAX_SEQUENCE
            and isinstance(self.payload, bytes) and len(self.payload) <= MAX_FRAME_SIZE
            and isinstance(self.mac, bytes) and len(self.mac) == MAC_SIZE and self.version == PROTOCOL_VERSION
        )


class SecureChannel:
    """Symmetric authenticated channel with replay defense and optional identity trust anchors."""

    def __init__(self, provider: KeyProvider, *, key_id: str, local_id: str, peer_id: str, session_id: str, direction: str,
                 identity_registry: IdentityRegistry | None = None, local_identity: AgentIdentity | None = None,
                 peer_identity: AgentIdentity | None = None):
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
        if any(value is not None for value in (identity_registry, local_identity, peer_identity)):
            if not isinstance(identity_registry, IdentityRegistry):
                raise ValueError("identity_registry_required")
            if not isinstance(local_identity, AgentIdentity) or not isinstance(peer_identity, AgentIdentity):
                raise ValueError("channel_identities_required")
            if local_identity.agent_id != local_id or peer_identity.agent_id != peer_id:
                raise ValueError("channel_identity_mismatch")
            if not identity_registry.is_trusted(local_identity) or not identity_registry.is_trusted(peer_identity):
                raise ValueError("channel_identity_untrusted")
        self._provider, self._key_id = provider, key_id
        self._local_id, self._peer_id = local_id, peer_id
        self._session_id, self._direction = session_id, direction
        self._identity_registry = identity_registry
        self._local_identity, self._peer_identity = local_identity, peer_identity
        self._send_sequence, self._last_received = 0, -1

    def _require_live_trust(self) -> None:
        if self._identity_registry is None:
            return
        if not isinstance(self._local_identity, AgentIdentity) or not self._identity_registry.is_trusted(self._local_identity):
            raise ValueError("channel_identity_untrusted")
        if not isinstance(self._peer_identity, AgentIdentity) or not self._identity_registry.is_trusted(self._peer_identity):
            raise ValueError("channel_identity_untrusted")
        if self._local_identity.agent_id != self._local_id or self._peer_identity.agent_id != self._peer_id:
            raise ValueError("channel_identity_mismatch")

    def _identity_binding(self) -> bytes:
        if self._identity_registry is None:
            return b""
        local_fp = _identity_fingerprint(self._local_identity)
        peer_fp = _identity_fingerprint(self._peer_identity)
        # Canonical pair binding is independent of endpoint perspective; direction
        # remains a separate derivation component, preventing reflection.
        pair = b"".join(sorted((local_fp, peer_fp)))
        return _IDENTITY_BINDING_DOMAIN + pair

    def _channel_key(self) -> bytes:
        try:
            root_key = self._provider.get_key(self._key_id)
        except Exception as exc:
            raise ValueError("channel_key_unavailable") from exc
        if not isinstance(root_key, bytes) or len(root_key) != KEY_SIZE:
            raise ValueError("channel_key_required")
        try:
            context = b"secure-channel/" + self._direction.encode("ascii") + self._identity_binding()
            return derive_subkey(root_key, salt=self._session_id.encode("utf-8"), context=context)
        except Exception as exc:
            raise ValueError("channel_key_derivation_failed") from exc

    def _authenticated_data(self) -> bytes:
        # This value must be identical from both endpoint perspectives.
        return _DOMAIN + PROTOCOL_VERSION.to_bytes(2, "big") + _field(self._session_id) + self._identity_binding()

    @staticmethod
    def _encode(version: int, sender_id: str, session_id: str, sequence: int, payload: bytes) -> bytes:
        return _DOMAIN + version.to_bytes(2, "big") + _field(sender_id) + _field(session_id) + sequence.to_bytes(8, "big") + len(payload).to_bytes(8, "big") + payload

    def _mac(self, sender_id: str, sequence: int, payload: bytes) -> bytes:
        signer = hmac.HMAC(self._channel_key(), hashes.SHA256())
        signer.update(self._authenticated_data())
        signer.update(self._encode(PROTOCOL_VERSION, sender_id, self._session_id, sequence, payload))
        return signer.finalize()

    def send(self, payload: bytes) -> SecureFrame:
        self._require_live_trust()
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
        self._require_live_trust()
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
