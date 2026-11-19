"""Fail-closed identity admission boundary for signed federated work.

This module authenticates envelope claims and checks durable membership before
nonce consumption. It deliberately does not construct a TaskSpec, select an
agent, grant capabilities, or bypass the receiving runtime's ActionGate.
Receivers must re-check current identity/revocation and evaluate each requested
capability against local policy immediately before execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
from typing import Protocol

from .federation_envelope import (
    EnvelopeRejected,
    ExecutionEnvelopeVerifier,
    SignedExecutionEnvelope,
)


class MembershipRegistry(Protocol):
    def is_registered(self, identity_id: str) -> bool: ...


_ADMISSION_PROOF_KEY = os.urandom(32)
_ADMISSION_ISSUER_TOKEN = object()


@dataclass(frozen=True)
class FederatedAdmission:
    execution_id: str
    principal_id: str
    agent_id: str
    task_type: str
    asserted_capabilities: tuple[str, ...]
    policy_version: str
    state_version: str
    issuer_key_id: str
    _proof: bytes = field(default=b"", repr=False, compare=False)

    def _proof_payload(self) -> bytes:
        return json.dumps(
            {
                "execution_id": self.execution_id,
                "principal_id": self.principal_id,
                "agent_id": self.agent_id,
                "task_type": self.task_type,
                "asserted_capabilities": list(self.asserted_capabilities),
                "policy_version": self.policy_version,
                "state_version": self.state_version,
                "issuer_key_id": self.issuer_key_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

    def is_verified(self) -> bool:
        if not isinstance(self._proof, bytes) or len(self._proof) != 32:
            return False
        try:
            expected = hmac.new(
                _ADMISSION_PROOF_KEY, self._proof_payload(), hashlib.sha256
            ).digest()
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(self._proof, expected)

    @classmethod
    def _from_verified_envelope(
        cls, envelope: SignedExecutionEnvelope, *, _issuer_token: object
    ) -> "FederatedAdmission":
        if _issuer_token is not _ADMISSION_ISSUER_TOKEN:
            raise PermissionError("federated_admission_issuer_only")
        admission = cls(
            execution_id=envelope.execution_id,
            principal_id=envelope.principal_id,
            agent_id=envelope.agent_id,
            task_type=envelope.task_type,
            asserted_capabilities=envelope.capabilities,
            policy_version=envelope.policy_version,
            state_version=envelope.state_version,
            issuer_key_id=envelope.issuer_key_id,
        )
        proof = hmac.new(
            _ADMISSION_PROOF_KEY, admission._proof_payload(), hashlib.sha256
        ).digest()
        return cls(
            execution_id=admission.execution_id,
            principal_id=admission.principal_id,
            agent_id=admission.agent_id,
            task_type=admission.task_type,
            asserted_capabilities=admission.asserted_capabilities,
            policy_version=admission.policy_version,
            state_version=admission.state_version,
            issuer_key_id=admission.issuer_key_id,
            _proof=proof,
        )


class FederatedAdmissionBoundary:
    """Verify signed claims against separate principal and agent trust stores."""

    def __init__(
        self,
        verifier: ExecutionEnvelopeVerifier,
        *,
        principal_registry: MembershipRegistry,
        agent_registry: MembershipRegistry,
    ) -> None:
        if not callable(getattr(verifier, "verify_and_consume", None)):
            raise TypeError("execution_envelope_verifier_required")
        if not callable(getattr(principal_registry, "is_registered", None)):
            raise TypeError("principal_membership_registry_required")
        if not callable(getattr(agent_registry, "is_registered", None)):
            raise TypeError("agent_membership_registry_required")
        self._verifier = verifier
        self._principals = principal_registry
        self._agents = agent_registry

    @staticmethod
    def _registered(registry: MembershipRegistry, identity_id: str, label: str) -> None:
        try:
            registered = registry.is_registered(identity_id)
        except Exception:
            raise EnvelopeRejected(f"{label}_membership_check_unavailable") from None
        if registered is not True:
            raise EnvelopeRejected(f"unregistered_{label}")

    def admit(self, envelope: SignedExecutionEnvelope) -> FederatedAdmission:
        if not isinstance(envelope, SignedExecutionEnvelope):
            raise EnvelopeRejected("invalid_execution_envelope")

        # Membership is checked before consuming the one-use nonce, so unknown
        # identities cannot burn a legitimate envelope's replay token.
        self._registered(self._principals, envelope.principal_id, "principal")
        self._registered(self._agents, envelope.agent_id, "agent")

        # The verifier independently checks signature, issuer trust, revocation,
        # freshness and replay. Its revocation callbacks must be wired to the
        # same durable trust stores (or an equally authoritative source).
        verified = self._verifier.verify_and_consume(envelope)
        if verified != envelope:
            raise EnvelopeRejected("verified_envelope_mismatch")

        return FederatedAdmission._from_verified_envelope(
            envelope, _issuer_token=_ADMISSION_ISSUER_TOKEN
        )
