"""Cryptographic agent identity, trust anchors, and signed attestation primitives."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


IDENTITY_VERSION: Final[int] = 1
PUBLIC_KEY_SIZE: Final[int] = 32
SIGNATURE_SIZE: Final[int] = 64
MAX_ID_SIZE: Final[int] = 1024
MAX_STATEMENT_SIZE: Final[int] = 16 * 1024 * 1024
_DOMAIN: Final[bytes] = b"noryx7/agent-identity/v1/"


def _identity_field(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_ID_SIZE:
        raise ValueError("identity_field_size_exceeded")
    return len(encoded).to_bytes(4, "big") + encoded


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    public_key: bytes
    version: int = IDENTITY_VERSION

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.agent_id, str)
            and bool(self.agent_id.strip())
            and len(self.agent_id.encode("utf-8")) <= MAX_ID_SIZE
            and isinstance(self.public_key, bytes)
            and len(self.public_key) == PUBLIC_KEY_SIZE
            and self.version == IDENTITY_VERSION
        )


@dataclass(frozen=True)
class AgentAttestation:
    identity: AgentIdentity
    statement: bytes
    signature: bytes

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.identity, AgentIdentity)
            and self.identity.is_well_formed()
            and isinstance(self.statement, bytes)
            and len(self.statement) <= MAX_STATEMENT_SIZE
            and isinstance(self.signature, bytes)
            and len(self.signature) == SIGNATURE_SIZE
        )


def _identity_bytes(identity: AgentIdentity) -> bytes:
    if not identity.is_well_formed():
        raise ValueError("invalid_agent_identity")
    return _DOMAIN + identity.version.to_bytes(2, "big") + _identity_field(identity.agent_id) + identity.public_key


def _attestation_message(identity: AgentIdentity, statement: bytes) -> bytes:
    if not isinstance(statement, bytes):
        raise TypeError("statement_must_be_bytes")
    if len(statement) > MAX_STATEMENT_SIZE:
        raise ValueError("statement_size_exceeded")
    return _identity_bytes(identity) + len(statement).to_bytes(8, "big") + statement


class IdentityRegistry:
    """Explicit trust-anchor registry mapping agent IDs to approved public keys."""

    def __init__(self):
        self._keys: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def register(self, identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        with self._lock:
            if identity.agent_id in self._keys:
                raise ValueError("agent_identity_already_registered")
            self._keys[identity.agent_id] = bytes(identity.public_key)

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._keys.pop(agent_id, None)

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            return self._keys.get(identity.agent_id) == identity.public_key


class AgentIdentityAuthority:
    """Creates and verifies Ed25519-backed agent identities and attestations."""

    @staticmethod
    def generate(agent_id: str) -> tuple[AgentIdentity, Ed25519PrivateKey]:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if len(agent_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("agent_id_size_exceeded")
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return AgentIdentity(agent_id, public_key), private_key

    @staticmethod
    def sign(identity: AgentIdentity, private_key: Ed25519PrivateKey, statement: bytes) -> AgentAttestation:
        if not identity.is_well_formed() or not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("invalid_identity_signing_context")
        raw_public = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        if raw_public != identity.public_key:
            raise ValueError("identity_private_key_mismatch")
        signature = private_key.sign(_attestation_message(identity, statement))
        return AgentAttestation(identity, bytes(statement), signature)

    @staticmethod
    def verify(attestation: AgentAttestation, registry: IdentityRegistry | None = None) -> bool:
        if not isinstance(attestation, AgentAttestation) or not attestation.is_well_formed():
            return False
        if registry is not None and not registry.is_trusted(attestation.identity):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(attestation.identity.public_key).verify(
                attestation.signature,
                _attestation_message(attestation.identity, attestation.statement),
            )
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    @staticmethod
    def verify_identity(identity: AgentIdentity, registry: IdentityRegistry | None = None) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        return registry is None or registry.is_trusted(identity)
