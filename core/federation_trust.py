"""Factories that bind federated verification to authoritative identity stores."""
from __future__ import annotations

from typing import Callable, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .federation_admission import FederatedAdmissionBoundary, MembershipRegistry
from .federation_envelope import (
    ExecutionEnvelopeVerifier,
    ReplayStore,
)


class RevocationRegistry(MembershipRegistry):
    def is_revoked(self, identity_id: str) -> bool: ...


def build_federated_admission_boundary(
    *,
    trusted_public_keys: Mapping[str, bytes | Ed25519PublicKey],
    replay_store: ReplayStore,
    principal_registry: RevocationRegistry,
    agent_registry: RevocationRegistry,
    is_issuer_revoked: Callable[[str], bool],
    clock: Callable[[], int],
    max_lifetime_seconds: int = 300,
    allowed_clock_skew_seconds: int = 5,
) -> FederatedAdmissionBoundary:
    """Build admission with revocation callbacks bound to the supplied stores.

    This prevents a caller from accidentally wiring no-op principal/agent
    revocation callbacks while still using the durable membership registries.
    Issuer revocation remains an explicit external trust-store responsibility.
    """
    for registry, label in (
        (principal_registry, "principal"),
        (agent_registry, "agent"),
    ):
        if not callable(getattr(registry, "is_registered", None)):
            raise TypeError(f"{label}_membership_registry_required")
        if not callable(getattr(registry, "is_revoked", None)):
            raise TypeError(f"{label}_revocation_registry_required")
    if not callable(is_issuer_revoked):
        raise TypeError("issuer_revocation_registry_required")

    verifier = ExecutionEnvelopeVerifier(
        trusted_public_keys,
        replay_store,
        is_issuer_revoked=is_issuer_revoked,
        is_principal_revoked=principal_registry.is_revoked,
        is_agent_revoked=agent_registry.is_revoked,
        clock=clock,
        max_lifetime_seconds=max_lifetime_seconds,
        allowed_clock_skew_seconds=allowed_clock_skew_seconds,
    )
    return FederatedAdmissionBoundary(
        verifier,
        principal_registry=principal_registry,
        agent_registry=agent_registry,
    )
