"""Fail-closed adapters from federated memory transfer to durable identity stores.

The v1 profile deliberately binds issuer_key_id to source_principal_id. Agent
ownership is a separate relationship and must be checked by an authoritative
principal/agent binding store supplied by the runtime; an AgentIdentity alone
does not prove which principal owns it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .memory_transfer import ed25519_signature_verifier


@dataclass(frozen=True)
class MemoryTransferTrust:
    """Trusted callbacks required by open_memory_transfer()."""

    verify_signature: Callable[[str, bytes, str], bool]
    verify_source_principal: Callable[[str, str], bool]
    verify_source_agent: Callable[[str, str], bool]
    verify_recipient_agent: Callable[[str, str], bool]


def build_memory_transfer_trust(
    *,
    principal_registry: object,
    agent_registry: object,
    is_agent_owned_by_principal: Callable[[str, str], bool] | None = None,
    binding_registry: object | None = None,
) -> MemoryTransferTrust:
    """Bind transfer verification to live, durable principal and agent stores.

    Requirements:
    - principal_registry.with_trusted_principal(principal_id, callback) must
      fail on missing/revoked identities and pass the current PrincipalIdentity.
    - agent_registry.with_trusted_identity(agent_id, callback) must fail on
      missing/revoked identities and pass the current AgentIdentity.
    - is_agent_owned_by_principal must consult an authoritative, independently
      authenticated principal/agent binding registry and return exactly True.

    No key or ownership result is cached. Registry failures deny the transfer.
    """
    with_principal = getattr(principal_registry, "with_trusted_principal", None)
    with_agent = getattr(agent_registry, "with_trusted_identity", None)
    if not callable(with_principal):
        raise TypeError("durable_principal_trust_registry_required")
    if not callable(with_agent):
        raise TypeError("durable_agent_trust_registry_required")
    if binding_registry is not None:
        if is_agent_owned_by_principal is not None:
            raise TypeError("ambiguous_principal_agent_binding_source")
        is_agent_owned_by_principal = getattr(
            binding_registry, "is_agent_owned_by_principal", None
        )
    if not callable(is_agent_owned_by_principal):
        raise TypeError("principal_agent_binding_verifier_required")

    def resolve_issuer_key(issuer_key_id: str) -> bytes | None:
        # v1 uses a canonical issuer identifier: the principal ID itself.
        if not isinstance(issuer_key_id, str) or not issuer_key_id.strip():
            return None
        try:
            return with_principal(
                issuer_key_id, lambda identity: bytes(identity.public_key)
            )
        except Exception:
            return None

    def verify_source_principal(issuer_key_id: str, source_principal_id: str) -> bool:
        if (
            not isinstance(issuer_key_id, str)
            or not isinstance(source_principal_id, str)
            or issuer_key_id != source_principal_id
        ):
            return False
        try:
            return with_principal(source_principal_id, lambda identity: (
                identity.principal_id == source_principal_id
                and isinstance(identity.public_key, bytes)
                and len(identity.public_key) == 32
            )) is True
        except Exception:
            return False

    def verify_agent_owner(principal_id: str, agent_id: str) -> bool:
        if (
            not isinstance(principal_id, str) or not principal_id.strip()
            or not isinstance(agent_id, str) or not agent_id.strip()
        ):
            return False
        try:
            def verify_agent(_principal_identity):
                owner_matches = is_agent_owned_by_principal(principal_id, agent_id) is True
                if not owner_matches:
                    return False
                return with_agent(agent_id, lambda identity: (
                    identity.agent_id == agent_id
                    and isinstance(identity.public_key, bytes)
                    and len(identity.public_key) == 32
                )) is True

            # Both sides of the relationship must still be trusted. A valid
            # agent key cannot outlive revocation of its owning principal.
            return with_principal(principal_id, verify_agent) is True
        except Exception:
            return False

    return MemoryTransferTrust(
        verify_signature=ed25519_signature_verifier(resolve_issuer_key),
        verify_source_principal=verify_source_principal,
        verify_source_agent=verify_agent_owner,
        verify_recipient_agent=verify_agent_owner,
    )
