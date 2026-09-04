from __future__ import annotations

import base64
import json
from dataclasses import dataclass, replace
from typing import Protocol

from .contracts import Attestation


_DOMAIN = b"NORYX7/runtime-attestation/v1/"


class AttestationSigner(Protocol):
    def sign(self, attestation: Attestation) -> bytes: ...
    def verify(self, attestation: Attestation, signature: bytes) -> bool: ...


def _message(attestation: Attestation) -> bytes:
    payload = {
        "domain": base64.b64encode(_DOMAIN).decode("ascii"),
        "execution_id": attestation.execution_id,
        "principal_id": attestation.principal_id,
        "step_id": attestation.step_id,
        "agent_id": attestation.agent_id,
        "action_digest": attestation.action_digest,
        "output_digest": attestation.output_digest,
        "verified": attestation.verified,
        "detail": attestation.detail,
    }
    return _DOMAIN + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


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
        self._validate(attestation)
        return self.private_key.sign(_message(attestation))

    def verify(self, attestation: Attestation, signature: bytes) -> bool:
        self._validate(attestation)
        if not isinstance(signature, bytes) or len(signature) != 64:
            return False
        try:
            self.private_key.public_key().verify(signature, _message(attestation))
        except Exception:
            return False
        return True

    @staticmethod
    def _validate(attestation: Attestation) -> None:
        if not isinstance(attestation, Attestation):
            raise TypeError("attestation must be an Attestation")
        fields = (
            attestation.execution_id,
            attestation.principal_id,
            attestation.step_id,
            attestation.agent_id,
            attestation.action_digest,
            attestation.output_digest,
        )
        if any(not isinstance(value, str) or not value for value in fields):
            raise ValueError("attestation identity and digests are required")
        for digest in (attestation.action_digest, attestation.output_digest):
            if len(digest) != 64:
                raise ValueError("attestation digest must be SHA-256 hex")
            try:
                int(digest, 16)
            except ValueError as exc:
                raise ValueError("attestation digest is not hexadecimal") from exc
        if not isinstance(attestation.verified, bool) or not isinstance(attestation.detail, str):
            raise ValueError("invalid attestation fields")


def signed_attestation(attestation: Attestation, signer: AttestationSigner) -> Attestation:
    if not callable(getattr(signer, "sign", None)):
        raise TypeError("signer must expose sign")
    signature = signer.sign(attestation)
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ValueError("signer returned an invalid Ed25519 signature")
    return replace(attestation, signature=signature)


def verify_attestation(attestation: Attestation, signer: AttestationSigner) -> bool:
    if not callable(getattr(signer, "verify", None)):
        raise TypeError("signer must expose verify")
    return bool(signer.verify(attestation, attestation.signature))
