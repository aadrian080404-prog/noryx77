"""Cryptographic attestations for NORYX7 stage and capability integrity."""

from __future__ import annotations

import hashlib
import hmac
import inspect
from dataclasses import dataclass
from typing import Any

from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class StageAttestation:
    task_id: str
    stage: str
    sequence: int
    risk_class: str
    verification_requirements: tuple[str, ...]
    payload_digest: str
    previous_tag: str
    tag: str


@dataclass(frozen=True)
class CapabilityAttestation:
    capability: str
    risk_class: str
    handler_fingerprint: str
    version: int
    tag: str


class HypersynthAttestation:
    """Fail-closed authenticated bindings across the HYPERSYNTH pipeline."""

    MAX_STAGE_LENGTH = 64
    MAX_TASK_LENGTH = 256
    MAX_CAPABILITY_LENGTH = 128
    MAX_REQUIREMENTS = 32
    MAX_SEQUENCE = 2**64 - 1
    _ATTESTATION_NONCE = "attestation"

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        self.crypto = crypto
        self._sequence = 0
        self._previous = ""
        self._revoked: dict[str, str] = {}
        self._capabilities: dict[str, CapabilityAttestation] = {}

    @staticmethod
    def _text(value: Any, name: str, limit: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"invalid_{name}")
        return value

    @staticmethod
    def handler_fingerprint(handler: Any) -> str:
        """Stable implementation fingerprint for functions and callable objects."""
        try:
            target = handler.__func__ if inspect.ismethod(handler) else handler
            module = getattr(target, "__module__", type(target).__module__)
            qualname = getattr(target, "__qualname__", type(target).__qualname__)
            code = getattr(target, "__code__", None)
            if code is not None:
                material = module.encode() + b"\0" + qualname.encode() + b"\0" + code.co_code
                material += repr(code.co_consts).encode("utf-8")
            else:
                call = getattr(target, "__call__", None)
                call_code = getattr(call, "__code__", None)
                material = module.encode() + b"\0" + qualname.encode()
                if call_code is not None:
                    material += b"\0" + call_code.co_code + repr(call_code.co_consts).encode("utf-8")
            return hashlib.sha256(material).hexdigest()
        except Exception as exc:
            raise TypeError("unfingerprintable_handler") from exc

    def _stage_payload(self, task_id: str, stage: str, risk_class: str,
                       requirements: tuple[str, ...], payload: Any,
                       sequence: int, previous_tag: str) -> dict[str, Any]:
        self._text(task_id, "task_id", self.MAX_TASK_LENGTH)
        self._text(stage, "stage", self.MAX_STAGE_LENGTH)
        self._text(risk_class, "risk_class", 32)
        if not isinstance(requirements, tuple) or len(requirements) > self.MAX_REQUIREMENTS:
            raise ValueError("invalid_verification_requirements")
        if any(not isinstance(item, str) or not item.strip() for item in requirements):
            raise ValueError("invalid_verification_requirements")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0 or sequence > self.MAX_SEQUENCE:
            raise ValueError("invalid_attestation_sequence")
        return {
            "task_id": task_id,
            "stage": stage,
            "risk_class": risk_class,
            "verification_requirements": requirements,
            "payload_digest": self.crypto.digest("hypersynth_payload", payload),
            "sequence": sequence,
            "previous_tag": previous_tag,
        }

    def attest_stage(self, task_id: str, stage: str, risk_class: str,
                     verification_requirements: tuple[str, ...], payload: Any) -> StageAttestation:
        if self._sequence >= self.MAX_SEQUENCE:
            raise OverflowError("attestation_sequence_exhausted")
        sequence = self._sequence + 1
        body = self._stage_payload(task_id, stage, risk_class, verification_requirements, payload, sequence, self._previous)
        envelope = self.crypto.sign("hypersynth_stage", body, sequence, nonce=self._ATTESTATION_NONCE)
        attestation = StageAttestation(task_id, stage, sequence, risk_class, verification_requirements,
                                       body["payload_digest"], self._previous, envelope.tag)
        self._sequence = sequence
        self._previous = envelope.tag
        return attestation

    def verify_stage(self, attestation: StageAttestation, payload: Any, *, consume: bool = False) -> bool:
        if not isinstance(attestation, StageAttestation):
            return False
        try:
            body = self._stage_payload(attestation.task_id, attestation.stage, attestation.risk_class,
                                       attestation.verification_requirements, payload,
                                       attestation.sequence, attestation.previous_tag)
            envelope = self.crypto.sign("hypersynth_stage", body, attestation.sequence, nonce=self._ATTESTATION_NONCE)
            if not hmac.compare_digest(envelope.tag, attestation.tag):
                return False
            if attestation.previous_tag and len(attestation.previous_tag) != 64:
                return False
            return True
        except Exception:
            return False

    def attest_capability(self, capability: str, risk_class: str, handler: Any, version: int = 1) -> CapabilityAttestation:
        capability = self._text(capability, "capability", self.MAX_CAPABILITY_LENGTH)
        risk_class = self._text(risk_class, "risk_class", 32)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1 or version >= 2**32:
            raise ValueError("invalid_capability_version")
        fingerprint = self.handler_fingerprint(handler)
        payload = {"capability": capability, "risk_class": risk_class, "handler_fingerprint": fingerprint, "version": version}
        tag = self.crypto.digest("capability_binding", payload)
        attestation = CapabilityAttestation(capability, risk_class, fingerprint, version, tag)
        existing = self._capabilities.get(capability)
        if existing is not None and existing != attestation:
            raise ValueError("capability_binding_conflict")
        self._capabilities[capability] = attestation
        return attestation

    def verify_capability(self, attestation: CapabilityAttestation, handler: Any, *, risk_class: str | None = None) -> bool:
        if not isinstance(attestation, CapabilityAttestation):
            return False
        if attestation.capability in self._revoked:
            return False
        try:
            if risk_class is not None and risk_class != attestation.risk_class:
                return False
            fingerprint = self.handler_fingerprint(handler)
            if fingerprint != attestation.handler_fingerprint:
                return False
            payload = {"capability": attestation.capability, "risk_class": attestation.risk_class,
                       "handler_fingerprint": fingerprint, "version": attestation.version}
            return self.crypto.verify_digest("capability_binding", payload, attestation.tag)
        except Exception:
            return False

    def revoke_capability(self, capability: str, reason: str) -> str:
        capability = self._text(capability, "capability", self.MAX_CAPABILITY_LENGTH)
        reason = self._text(reason, "revocation_reason", 256)
        if capability not in self._capabilities:
            raise KeyError("unknown_capability")
        token = self.crypto.digest("capability_revocation", {"capability": capability, "reason": reason})
        self._revoked[capability] = token
        return token

    def is_revoked(self, capability: str, reason: str | None = None) -> bool:
        if not isinstance(capability, str):
            return False
        token = self._revoked.get(capability)
        if token is None:
            return False
        if reason is None:
            return True
        try:
            expected = self.crypto.digest("capability_revocation", {"capability": capability, "reason": reason})
            return hmac.compare_digest(token, expected)
        except Exception:
            return False

    def attest_pipeline(self, task_id: str, risk_class: str,
                        verification_requirements: tuple[str, ...], stages: tuple[tuple[str, Any], ...]) -> tuple[StageAttestation, ...]:
        if not isinstance(stages, tuple) or not stages:
            raise ValueError("empty_pipeline")
        return tuple(self.attest_stage(task_id, stage, risk_class, verification_requirements, payload)
                     for stage, payload in stages)

    def verify_pipeline(self, attestations: tuple[StageAttestation, ...], payloads: tuple[Any, ...],
                        task_id: str, risk_class: str, requirements: tuple[str, ...]) -> bool:
        if not isinstance(attestations, tuple) or not isinstance(payloads, tuple) or len(attestations) != len(payloads) or not attestations:
            return False
        previous = ""
        expected_sequence = None
        for attestation, payload in zip(attestations, payloads):
            if not isinstance(attestation, StageAttestation):
                return False
            if attestation.task_id != task_id or attestation.risk_class != risk_class or attestation.verification_requirements != requirements:
                return False
            if expected_sequence is not None and attestation.sequence != expected_sequence + 1:
                return False
            if attestation.previous_tag != previous:
                return False
            if not self.verify_stage(attestation, payload):
                return False
            previous = attestation.tag
            expected_sequence = attestation.sequence
        return True
