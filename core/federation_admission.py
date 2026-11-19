"""Fail-closed identity admission boundary for signed federated work.

This module authenticates envelope claims and checks durable membership before
nonce consumption. It deliberately does not construct a TaskSpec, select an
agent, grant capabilities, or bypass the receiving runtime's ActionGate.
Receivers must re-check current identity/revocation and evaluate each requested
capability against local policy immediately before execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .federation_envelope import (
    EnvelopeRejected,
    ExecutionEnvelopeVerifier,
    SignedExecutionEnvelope,
)


class MembershipRegistry(Protocol):
    def is_registered(self, identity_id: str) -> bool: ...


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

        return FederatedAdmission(
            execution_id=envelope.execution_id,
            principal_id=envelope.principal_id,
            agent_id=envelope.agent_id,
            task_type=envelope.task_type,
            asserted_capabilities=envelope.capabilities,
            policy_version=envelope.policy_version,
            state_version=envelope.state_version,
            issuer_key_id=envelope.issuer_key_id,
        )
