"""Cryptographic agent identity, trust anchors, and signed attestation primitives."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable, Final, TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


IDENTITY_VERSION: Final[int] = 1
PUBLIC_KEY_SIZE: Final[int] = 32
SIGNATURE_SIZE: Final[int] = 64
MAX_ID_SIZE: Final[int] = 1024
MAX_STATEMENT_SIZE: Final[int] = 16 * 1024 * 1024
_DOMAIN: Final[bytes] = b"noryx7/agent-identity/v1/"
_ROTATION_DOMAIN: Final[bytes] = b"noryx7/agent-identity-rotation/v1/"
T = TypeVar("T")


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


def identity_rotation_message(
    agent_id: str,
    old_public_key: bytes,
    new_public_key: bytes,
    generation: int,
) -> bytes:
    """Return the domain-separated message both old and new keys must sign."""
    if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id.encode("utf-8")) > MAX_ID_SIZE:
        raise ValueError("invalid_agent_id")
    if not isinstance(old_public_key, bytes) or len(old_public_key) != PUBLIC_KEY_SIZE:
        raise ValueError("invalid_old_public_key")
    if not isinstance(new_public_key, bytes) or len(new_public_key) != PUBLIC_KEY_SIZE:
        raise ValueError("invalid_new_public_key")
    if old_public_key == new_public_key:
        raise ValueError("rotation_key_must_change")
    if (isinstance(generation, bool) or not isinstance(generation, int)
            or not 1 <= generation <= (2**64 - 1)):
        raise ValueError("invalid_identity_generation")
    return (
        _ROTATION_DOMAIN
        + _identity_field(agent_id)
        + generation.to_bytes(8, "big")
        + old_public_key
        + new_public_key
    )


class IdentityRegistry:
    """Trust-anchor registry with monotonic, dual-proof identity key rotation."""

    def __init__(self):
        self._keys: dict[str, bytes] = {}
        self._generations: dict[str, int] = {}
        self._revoked: set[str] = set()
        self._lock = threading.RLock()

    def register(self, identity: AgentIdentity) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        with self._lock:
            if identity.agent_id in self._revoked:
                raise PermissionError("agent_identity_permanently_revoked")
            if identity.agent_id in self._keys:
                raise ValueError("agent_identity_already_registered")
            self._keys[identity.agent_id] = bytes(identity.public_key)
            self._generations[identity.agent_id] = 1

    def revoke(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            self._keys.pop(agent_id, None)
            self._revoked.add(agent_id)

    def generation(self, agent_id: str) -> int:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        with self._lock:
            if agent_id in self._revoked or agent_id not in self._generations:
                raise PermissionError("agent_identity_not_active")
            return self._generations[agent_id]

    def rotate_identity(
        self,
        identity: AgentIdentity,
        *,
        expected_generation: int,
        old_key_signature: bytes,
        new_key_signature: bytes,
    ) -> int:
        """Atomically replace a trusted key only with old-key and new-key proof.

        Both signatures cover the same agent, current generation, old key and
        proposed key. The generation compare-and-swap prevents stale rotations.
        """
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        if (isinstance(expected_generation, bool) or not isinstance(expected_generation, int)
                or not 1 <= expected_generation <= (2**64 - 1)):
            raise ValueError("invalid_identity_generation")
        if not isinstance(old_key_signature, bytes) or len(old_key_signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_old_key_signature")
        if not isinstance(new_key_signature, bytes) or len(new_key_signature) != SIGNATURE_SIZE:
            raise ValueError("invalid_new_key_signature")

        with self._lock:
            agent_id = identity.agent_id
            current_key = self._keys.get(agent_id)
            current_generation = self._generations.get(agent_id)
            if agent_id in self._revoked or current_key is None:
                raise PermissionError("agent_identity_not_active")
            if current_generation != expected_generation:
                raise PermissionError("identity_generation_conflict")
            if current_key == identity.public_key:
                raise ValueError("rotation_key_must_change")

            message = identity_rotation_message(
                agent_id, current_key, identity.public_key, expected_generation
            )
            try:
                Ed25519PublicKey.from_public_bytes(current_key).verify(old_key_signature, message)
                Ed25519PublicKey.from_public_bytes(identity.public_key).verify(new_key_signature, message)
            except (InvalidSignature, ValueError, TypeError):
                raise PermissionError("identity_rotation_proof_invalid") from None

            if current_generation >= (2**64 - 1):
                raise OverflowError("identity_generation_exhausted")
            next_generation = current_generation + 1
            self._keys[agent_id] = bytes(identity.public_key)
            self._generations[agent_id] = next_generation
            return next_generation

    def is_trusted(self, identity: AgentIdentity) -> bool:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            return self._keys.get(identity.agent_id) == identity.public_key

    def with_trusted_identity(self, agent_id: str, callback: Callable[[AgentIdentity], T]) -> T:
        """Run a short verification/commit critical section against one live key.

        Revocation and key replacement cannot interleave with the callback. The
        callback is intended for bounded cryptographic verification and state
        commit only; it must not perform external I/O or invoke agent code.
        """
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            public_key = self._keys.get(agent_id)
            if public_key is None:
                raise PermissionError("agent_identity_not_trusted")
            return callback(AgentIdentity(agent_id, bytes(public_key)))


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
