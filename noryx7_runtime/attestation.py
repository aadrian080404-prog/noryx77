from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from typing import Protocol, Sequence

from core.identity import AgentIdentity, IdentityRegistry
from .contracts import Attestation

_DOMAIN = b"NORYX7/runtime-attestation/v5/"
_ZERO_DIGEST = "0" * 64
_MAX_FIELD_SIZE = 256
_MAX_DETAIL_SIZE = 4096


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
        "provenance_digest": attestation.provenance_digest,
        "provenance_seal": base64.b64encode(attestation.provenance_seal).decode("ascii"),
    }
    return _DOMAIN + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _valid_digest(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_attestation(attestation: Attestation) -> None:
    if not isinstance(attestation, Attestation):
        raise TypeError("attestation must be an Attestation")
    required_fields = (
        attestation.execution_id,
        attestation.principal_id,
        attestation.step_id,
        attestation.agent_id,
    )
    if any(
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > _MAX_FIELD_SIZE
        for value in required_fields
    ):
        raise ValueError("attestation identity fields are required and bounded")
    if not isinstance(attestation.runtime_id, str) or len(attestation.runtime_id.encode("utf-8")) > _MAX_FIELD_SIZE:
        raise ValueError("runtime_id must be bounded string")
    if not _valid_digest(attestation.agent_key_fingerprint):
        raise ValueError("attestation digest must be SHA-256 hex")
    if not _valid_digest(attestation.previous_attestation_digest):
        raise ValueError("previous attestation digest must be SHA-256 hex")
    if not _valid_digest(attestation.action_digest) or not _valid_digest(attestation.output_digest):
        raise ValueError("attestation digest must be 64-character SHA-256 hex")
    if not isinstance(attestation.verified, bool) or not isinstance(attestation.detail, str):
        raise ValueError("invalid attestation fields")
    if len(attestation.detail.encode("utf-8")) > _MAX_DETAIL_SIZE:
        raise ValueError("attestation detail size exceeded")
    if not isinstance(attestation.provenance_digest, str) or not isinstance(attestation.provenance_seal, bytes):
        raise ValueError("invalid provenance binding")
    if bool(attestation.provenance_digest) != bool(attestation.provenance_seal):
        raise ValueError("provenance digest and seal must be supplied together")
    if attestation.provenance_digest:
        if not _valid_digest(attestation.provenance_digest):
            raise ValueError("provenance digest must be SHA-256 hex")
        if len(attestation.provenance_seal) != 32:
            raise ValueError("provenance seal must be 32 bytes")


def attestation_digest(attestation) -> str:
    if not isinstance(attestation, Attestation):
        try:
            attestation = Attestation(
                execution_id=attestation.execution_id,
                principal_id=attestation.principal_id,
                step_id=attestation.step_id,
                agent_id=attestation.agent_id,
                agent_key_fingerprint=attestation.agent_key_fingerprint,
                action_digest=attestation.action_digest,
                output_digest=attestation.output_digest,
                verified=True,
                detail="verified",
                signature=attestation.signature,
                previous_attestation_digest=attestation.previous_attestation_digest,
                runtime_id=getattr(attestation, "runtime_id", ""),
                provenance_digest=getattr(attestation, "provenance_digest", ""),
                provenance_seal=getattr(attestation, "provenance_seal", b""),
            )
        except AttributeError as exc:
            raise TypeError("attestation must be an Attestation") from exc
    _validate_attestation(attestation)
    if not isinstance(attestation.signature, bytes) or len(attestation.signature) != 64:
        raise ValueError("attestation must carry a valid signature")
    return hashlib.sha256(_message(attestation) + attestation.signature).hexdigest()


@dataclass(frozen=True)
class Ed25519AttestationSigner:
    private_key: object

    def __post_init__(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        if not isinstance(self.private_key, Ed25519PrivateKey):
            raise TypeError("private_key must be an Ed25519 private key")

    @classmethod
    def generate(cls):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return cls(Ed25519PrivateKey.generate())

    @property
    def public_key_bytes(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self.private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def sign(self, attestation):
        _validate_attestation(attestation)
        return self.private_key.sign(_message(attestation))

    def verify(self, attestation, signature):
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
    def from_public_key_bytes(cls, public_key):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            raise ValueError("public_key must be 32 bytes")
        return cls(Ed25519PublicKey.from_public_bytes(public_key))

    def verify(self, attestation, signature):
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

    def __post_init__(self):
        if not isinstance(self.registry, IdentityRegistry):
            raise TypeError("registry must be an IdentityRegistry")

    def verify(self, attestation, signature):
        _validate_attestation(attestation)
        try:
            return bool(self.registry.with_trusted_identity(
                attestation.agent_id,
                lambda identity: self._verify_with_identity(identity, attestation, signature),
            ))
        except Exception:
            return False

    @staticmethod
    def _verify_with_identity(identity: AgentIdentity, attestation, signature):
        if hashlib.sha256(identity.public_key).hexdigest() != attestation.agent_key_fingerprint:
            return False
        return Ed25519AttestationVerifier.from_public_key_bytes(identity.public_key).verify(attestation, signature)


@dataclass(frozen=True)
class AttestationChainVerifier:
    """Fail-closed verifier for an ordered, execution-bound attestation chain."""
    verifier: AttestationVerifier

    def verify_chain(self, attestations: Sequence[Attestation]) -> bool:
        if not isinstance(attestations, (list, tuple)) or not attestations:
            return False
        previous_digest = _ZERO_DIGEST
        first = attestations[0]
        if not isinstance(first, Attestation):
            return False
        execution_id = first.execution_id
        principal_id = first.principal_id
        runtime_id = first.runtime_id
        for attestation in attestations:
            if not isinstance(attestation, Attestation):
                return False
            try:
                _validate_attestation(attestation)
            except (TypeError, ValueError):
                return False
            if (attestation.execution_id, attestation.principal_id, attestation.runtime_id) != (execution_id, principal_id, runtime_id):
                return False
            if not hmac.compare_digest(attestation.previous_attestation_digest, previous_digest):
                return False
            try:
                if not self.verifier.verify(attestation, attestation.signature):
                    return False
                previous_digest = attestation_digest(attestation)
            except (TypeError, ValueError):
                return False
        return True


def signed_attestation(attestation, signer):
    _validate_attestation(attestation)
    if not callable(getattr(signer, "sign", None)):
        raise TypeError("signer must expose sign")
    signature = signer.sign(attestation)
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ValueError("signer returned an invalid Ed25519 signature")
    return replace(attestation, signature=signature)


def verify_attestation(attestation, signer):
    _validate_attestation(attestation)
    if not callable(getattr(signer, "verify", None)):
        raise TypeError("signer must expose verify")
    return bool(signer.verify(attestation, attestation.signature))
