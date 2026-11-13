"""Authenticated session framing with strict cryptographic identity and replay protection."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .crypto import KEY_SIZE, KeyProvider, derive_subkey
from .identity import AgentIdentity, IdentityRegistry

MAC_SIZE: Final[int] = 16  # AES-GCM authentication tag size
MAX_FRAME_SIZE: Final[int] = 16 * 1024 * 1024
MAX_ID_SIZE: Final[int] = 1024
PROTOCOL_VERSION: Final[int] = 1
MAX_SEQUENCE: Final[int] = (1 << 64) - 1
REPLAY_WINDOW: Final[int] = 4096
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
            and isinstance(self.mac, bytes) and len(self.mac) == MAC_SIZE
            and isinstance(self.version, int) and not isinstance(self.version, bool) and self.version == PROTOCOL_VERSION
        )


class SecureChannel:
    """Confidential, authenticated AES-GCM channel with bounded replay defense.

    The caller must provide a fresh, never-reused session_id for every new
    channel key epoch. Sequence state is process-local; session rotation is
    mandatory after process restart or state loss.
    """

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
        self._received_sequences: set[int] = set()
        self._send_lock = Lock()
        self._receive_lock = Lock()

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
        return _DOMAIN + PROTOCOL_VERSION.to_bytes(2, "big") + _field(self._session_id) + self._identity_binding()


    def _nonce(self, sender_id: str, sequence: int) -> bytes:
        prefix = sha256(
            _DOMAIN + _field(sender_id) + _field(self._session_id) + self._identity_binding()
        ).digest()[:4]
        return prefix + sequence.to_bytes(8, "big")

    def _aad(self, sender_id: str, sequence: int) -> bytes:
        return self._authenticated_data() + _field(sender_id) + sequence.to_bytes(8, "big")

    def _encrypt(self, sender_id: str, sequence: int, plaintext: bytes) -> tuple[bytes, bytes]:
        sealed = AESGCM(self._channel_key()).encrypt(
            self._nonce(sender_id, sequence), plaintext, self._aad(sender_id, sequence)
        )
        return sealed[:-MAC_SIZE], sealed[-MAC_SIZE:]

    def _decrypt(self, sender_id: str, sequence: int, ciphertext: bytes, tag: bytes) -> bytes:
        try:
            return AESGCM(self._channel_key()).decrypt(
                self._nonce(sender_id, sequence), ciphertext + tag, self._aad(sender_id, sequence)
            )
        except InvalidTag as exc:
            raise ValueError("frame_authentication_failed") from exc

    def send(self, payload: bytes) -> SecureFrame:
        if not isinstance(payload, bytes):
            raise TypeError("payload_must_be_bytes")
        if len(payload) > MAX_FRAME_SIZE:
            raise ValueError("frame_size_exceeded")
        with self._send_lock:
            self._require_live_trust()
            if self._send_sequence > MAX_SEQUENCE:
                raise ValueError("sequence_exhausted")
            sequence = self._send_sequence
            ciphertext, tag = self._encrypt(self._local_id, sequence, payload)
            self._send_sequence += 1
            return SecureFrame(self._local_id, self._session_id, sequence, ciphertext, tag)

    def receive(self, frame: SecureFrame) -> bytes:
        with self._receive_lock:
            self._require_live_trust()
            if not isinstance(frame, SecureFrame) or not frame.is_well_formed():
                raise ValueError("invalid_secure_frame")
            if frame.sender_id != self._peer_id or frame.session_id != self._session_id:
                raise ValueError("channel_identity_mismatch")
            if frame.sequence in self._received_sequences:
                raise ValueError("replayed_frame")
            if self._last_received >= 0 and frame.sequence + REPLAY_WINDOW <= self._last_received:
                raise ValueError("replayed_frame")
            try:
                plaintext = self._decrypt(frame.sender_id, frame.sequence, frame.payload, frame.mac)
            except Exception as exc:
                if isinstance(exc, ValueError) and str(exc) == "frame_authentication_failed":
                    raise
                raise ValueError("frame_authentication_failed") from exc
            self._received_sequences.add(frame.sequence)
            if frame.sequence > self._last_received:
                self._last_received = frame.sequence
            floor = self._last_received - REPLAY_WINDOW + 1
            if floor > 0:
                self._received_sequences.intersection_update(
                    sequence for sequence in self._received_sequences if sequence >= floor
                )
            return bytes(plaintext)

    @property
    def last_received_sequence(self) -> int:
        with self._receive_lock:
            return self._last_received
