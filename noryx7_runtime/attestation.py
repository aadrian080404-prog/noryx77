from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, replace
from typing import Protocol

from core.identity import AgentIdentity, IdentityRegistry

from .contracts import Attestation


_DOMAIN = b"NORYX7/runtime-attestation/v4/"
_ZERO_DIGEST = "0" * 64


class AttestationSigner(Protocol):
    def sign(self, attestation: Attestation) -> bytes: ...
    def verify(self, attestation: Attestation, signature: bytes) -> bool: ...


class AttestationVerifier(Protocol):
    def verify(self, attestation: Attestation, signature: bytes) -> bool: ...


def _message(attestation: Attestation) -> bytes:
    payload = {
        "domain": base64.b64encode(_DOMAIN).decode("ascii"),
        "execution_id": attestation.execution_id,
        "principal_id": attestation.principal_id,
        "step_id": attestation.step_id,
        "agent_id": attestation.agent_id,
        "agent_key_fingerprint": attestation.agent_key_fingerprint,
        "action_digest": attestation.action_digest,
        "output_digest": attestation.output_digest,
        "verified": attestation.verified,
        "detail": attestation.detail,
        "previous_attestation_digest": attestation.previous_attestation_digest,
        "runtime_id": attestation.runtime_id,
    }
    return _DOMAIN + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _validate_attestation(attestation: Attestation) -> None:
    if not isinstance(attestation, Attestation):
        raise TypeError("attestation must be an Attestation")
    fields = (
        attestation.execution_id,
        attestation.principal_id,
        attestation.step_id,
        attestation.agent_id,
        attestation.agent_key_fingerprint,
        attestation.action_digest,
        attestation.output_digest,
        attestation.previous_attestation_digest,
    )
    if any(not isinstance(value, str) or not value for value in fields):
        raise ValueError("attestation identity and digests are required")
    if not isinstance(attestation.runtime_id, str):
        raise ValueError("runtime_id must be a string")
    for digest in fields[4:]:
        if len(digest) != 64:
            raise ValueError("attestation digest must be SHA-256 hex")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise ValueError("attestation digest is not hexadecimal") from exc
    if not isinstance(attestation.verified, bool) or not isinstance(attestation.detail, str):
        raise ValueError("invalid attestation fields")


def attestation_digest(attestation: Attestation) -> str:
    """Return the immutable digest of a signed attestation."""
    _validate_attestation(attestation)
    if not isinstance(attestation.signature, bytes) or len(attestation.signature) != 64:
        raise ValueError("attestation must carry a valid signature")
    payload = _message(attestation) + attestation.signature
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Ed25519AttestationSigner:
    private_key: object

    def __post_init__(self) -> None:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError as exc:
            raise RuntimeError("cryptography is required for attestation signing") from exc
        if not isinstance(self.private_key, Ed25519PrivateKey):
            raise TypeError("private_key must be an Ed25519 private key")

    @classmethod
    def generate(cls) -> "Ed25519AttestationSigner":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return cls(Ed25519PrivateKey.generate())

    @property
    def public_key_bytes(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    def sign(self, attestation: Attestation) -> bytes:
        _validate_attestation(attestation)
        return self.private_key.sign(_message(attestation))

    def verify(self, attestation: Attestation, signature: bytes) -> bool:
        _validate_attestation(attestation)
        if not isinstance(signature, bytes) or len(signature) != 64:
            return False
        try:
            self.private_key.public_key().verify(signature, _message(attestation))
        except Exception:
            return False
        return True


@dataclass(frozen=True)
class Ed25519AttestationVerifier:
    public_key: object

    def __post_init__(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        if not isinstance(self.public_key, Ed25519PublicKey):
            raise TypeError("public_key must be an Ed25519 public key")

    @classmethod
    def from_public_key_bytes(cls, public_key: bytes) -> "Ed25519AttestationVerifier":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            raise ValueError("public_key must be 32 bytes")
        return cls(Ed25519PublicKey.from_public_bytes(public_key))

    def verify(self, attestation: Attestation, signature: bytes) -> bool:
        _validate_attestation(attestation)
        if not isinstance(signature, bytes) or len(signature) != 64:
            return False
        try:
            self.public_key.verify(signature, _message(attestation))
        except Exception:
            return False
        return True


@dataclass(frozen=True)
class IdentityBoundAttestationVerifier:
    registry: IdentityRegistry

    def __post_init__(self) -> None:
        if not isinstance(self.registry, IdentityRegistry):
            raise TypeError("registry must be an IdentityRegistry")

    def verify(self, attestation: Attestation, signature: bytes) -> bool:
        _validate_attestation(attestation)
        try:
            return bool(self.registry.with_trusted_identity(
                attestation.agent_id,
                lambda identity: self._verify_with_identity(identity, attestation, signature),
            ))
        except Exception:
            return False

    @staticmethod
    def _verify_with_identity(identity: AgentIdentity, attestation: Attestation, signature: bytes) -> bool:
        fingerprint = hashlib.sha256(identity.public_key).hexdigest()
        if fingerprint != attestation.agent_key_fingerprint:
            return False
        return Ed25519AttestationVerifier.from_public_key_bytes(identity.public_key).verify(attestation, signature)


def signed_attestation(attestation: Attestation, signer: AttestationSigner) -> Attestation:
    _validate_attestation(attestation)
    if not callable(getattr(signer, "sign", None)):
        raise TypeError("signer must expose sign")
    signature = signer.sign(attestation)
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ValueError("signer returned an invalid Ed25519 signature")
    return replace(attestation, signature=signature)


def verify_attestation(attestation: Attestation, signer: AttestationSigner) -> bool:
    _validate_attestation(attestation)
    if not callable(getattr(signer, "verify", None)):
        raise TypeError("signer must expose verify")
    return bool(signer.verify(attestation, attestation.signature))
