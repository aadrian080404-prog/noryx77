"""Distinct principal identity primitives and an in-memory trust registry.

Principal identities represent users or tenants. They are intentionally
separate from agent identities, which identify executable NORYX7 agents.
Registration is a privileged provisioning operation; this module does not
authenticate a person or provide an external identity provider.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable, TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

PRINCIPAL_IDENTITY_VERSION = 1
PRINCIPAL_PUBLIC_KEY_SIZE = 32
PRINCIPAL_SIGNATURE_SIZE = 64
MAX_PRINCIPAL_ID_SIZE = 256
MAX_PRINCIPAL_STATEMENT_SIZE = 64 * 1024
_PRINCIPAL_DOMAIN = b"NORYX7/PRINCIPAL_IDENTITY/v1:"
T = TypeVar("T")


@dataclass(frozen=True)
class PrincipalIdentity:
    principal_id: str
    public_key: bytes
    version: int = PRINCIPAL_IDENTITY_VERSION

    def is_well_formed(self) -> bool:
        if not isinstance(self.principal_id, str) or not self.principal_id.strip():
            return False
        try:
            encoded_id = self.principal_id.encode("utf-8")
        except UnicodeEncodeError:
            return False
        return (
            len(encoded_id) <= MAX_PRINCIPAL_ID_SIZE
            and isinstance(self.public_key, bytes)
            and len(self.public_key) == PRINCIPAL_PUBLIC_KEY_SIZE
            and isinstance(self.version, int)
            and not isinstance(self.version, bool)
            and self.version == PRINCIPAL_IDENTITY_VERSION
        )


@dataclass(frozen=True)
class PrincipalProof:
    identity: PrincipalIdentity
    statement: bytes
    signature: bytes

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.identity, PrincipalIdentity)
            and self.identity.is_well_formed()
            and isinstance(self.statement, bytes)
            and len(self.statement) <= MAX_PRINCIPAL_STATEMENT_SIZE
            and isinstance(self.signature, bytes)
            and len(self.signature) == PRINCIPAL_SIGNATURE_SIZE
        )


def _principal_message(identity: PrincipalIdentity, statement: bytes) -> bytes:
    if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
        raise ValueError("invalid_principal_identity")
    if not isinstance(statement, bytes) or len(statement) > MAX_PRINCIPAL_STATEMENT_SIZE:
        raise ValueError("invalid_principal_statement")
    principal_id = identity.principal_id.encode("utf-8")
    return (
        _PRINCIPAL_DOMAIN
        + identity.version.to_bytes(2, "big")
        + len(principal_id).to_bytes(4, "big")
        + principal_id
        + identity.public_key
        + len(statement).to_bytes(4, "big")
        + statement
    )


class PrincipalIdentityAuthority:
    """Creates Ed25519 principal identities and proofs of key possession."""

    @staticmethod
    def generate(principal_id: str) -> tuple[PrincipalIdentity, Ed25519PrivateKey]:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("invalid_principal_id")
        try:
            encoded = principal_id.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_principal_id") from exc
        if len(encoded) > MAX_PRINCIPAL_ID_SIZE:
            raise ValueError("principal_id_size_exceeded")
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return PrincipalIdentity(principal_id, public_key), private_key

    @staticmethod
    def prove(
        identity: PrincipalIdentity,
        private_key: Ed25519PrivateKey,
        statement: bytes,
    ) -> PrincipalProof:
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("ed25519_private_key_required")
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        if not identity.is_well_formed() or public_key != identity.public_key:
            raise ValueError("principal_private_key_mismatch")
        if not isinstance(statement, bytes) or len(statement) > MAX_PRINCIPAL_STATEMENT_SIZE:
            raise ValueError("invalid_principal_statement")
        return PrincipalProof(
            identity=identity,
            statement=statement,
            signature=private_key.sign(_principal_message(identity, statement)),
        )

    @staticmethod
    def verify(proof: PrincipalProof) -> bool:
        if not isinstance(proof, PrincipalProof) or not proof.is_well_formed():
            return False
        try:
            Ed25519PublicKey.from_public_bytes(proof.identity.public_key).verify(
                proof.signature, _principal_message(proof.identity, proof.statement)
            )
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


class PrincipalIdentityRegistry:
    """Thread-safe in-memory principal trust registry with permanent tombstones."""

    def __init__(self) -> None:
        self._principals: dict[str, bytes] = {}
        self._revoked: set[str] = set()
        self._lock = threading.RLock()

    def register(self, identity: PrincipalIdentity) -> None:
        if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_principal_identity")
        with self._lock:
            if identity.principal_id in self._revoked:
                raise PermissionError("principal_identity_permanently_revoked")
            if identity.principal_id in self._principals:
                raise ValueError("principal_identity_already_registered")
            self._principals[identity.principal_id] = bytes(identity.public_key)

    def revoke(self, principal_id: str) -> None:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("invalid_principal_id")
        try:
            if len(principal_id.encode("utf-8")) > MAX_PRINCIPAL_ID_SIZE:
                raise ValueError("invalid_principal_id")
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_principal_id") from exc
        with self._lock:
            self._revoked.add(principal_id)
            self._principals.pop(principal_id, None)

    def is_revoked(self, principal_id: str) -> bool:
        if not isinstance(principal_id, str) or not principal_id.strip():
            return True
        try:
            if len(principal_id.encode("utf-8")) > MAX_PRINCIPAL_ID_SIZE:
                return True
        except UnicodeEncodeError:
            return True
        with self._lock:
            return principal_id in self._revoked

    def is_trusted(self, identity: PrincipalIdentity) -> bool:
        if not isinstance(identity, PrincipalIdentity) or not identity.is_well_formed():
            return False
        with self._lock:
            return (
                identity.principal_id not in self._revoked
                and self._principals.get(identity.principal_id) == identity.public_key
            )

    def with_trusted_principal(
        self, principal_id: str, callback: Callable[[PrincipalIdentity], T]
    ) -> T:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("invalid_principal_id")
        try:
            if len(principal_id.encode("utf-8")) > MAX_PRINCIPAL_ID_SIZE:
                raise ValueError("invalid_principal_id")
        except UnicodeEncodeError as exc:
            raise ValueError("invalid_principal_id") from exc
        if not callable(callback):
            raise TypeError("callback_must_be_callable")
        with self._lock:
            if principal_id in self._revoked:
                raise PermissionError("principal_identity_permanently_revoked")
            public_key = self._principals.get(principal_id)
            if public_key is None:
                raise PermissionError("principal_identity_not_trusted")
            return callback(PrincipalIdentity(principal_id, bytes(public_key)))
