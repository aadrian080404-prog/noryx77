"""Explicit fail-closed composition for the durable trust runtime.

This factory is deliberately opt-in. It refuses ephemeral registries/replay
guards, missing principal-agent ownership checks, unavailable external signing
keys, and witness/local epoch divergence before returning a TrustChain.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.authorization_replay import ReplayGuard
from core.identity import AgentIdentity
from core.sqlite_agent_identity_registry import SQLiteAgentIdentityRegistry
from core.sqlite_authorization_replay import SQLiteAuthorizationReplayGuard
from core.trust_chain import TrustChain
from core.trust_providers import (
    MonotonicWitness,
    SigningKeyProvider,
    require_witness_epoch,
    sign_for_identity,
)

_BOOTSTRAP_DOMAIN = b"noryx7/durable-runtime-bootstrap/v1/"


@dataclass(frozen=True)
class DurableTrustRuntime:
    """Validated trust components; callers still control route readiness."""

    trust_chain: TrustChain
    identity_registry: SQLiteAgentIdentityRegistry
    replay_guard: SQLiteAuthorizationReplayGuard
    agent_identity: AgentIdentity
    key_id: str
    witness_namespace: str
    epoch: int


def build_durable_trust_runtime(
    *,
    identity_registry: SQLiteAgentIdentityRegistry,
    replay_guard: SQLiteAuthorizationReplayGuard,
    key_provider: SigningKeyProvider,
    key_id: str,
    agent_identity: AgentIdentity,
    witness: MonotonicWitness,
    witness_namespace: str,
    local_epoch: int,
    principal_id: str,
    principal_agent_binding_verifier,
) -> DurableTrustRuntime:
    """Construct durable TrustChain only after all trust dependencies self-check.

    The binding verifier must query the live durable principal-agent registry;
    a cached admission or a truthy value other than literal True is rejected.
    The key-provider challenge proves that the configured key handle is
    available and matches the registered public key without exporting a key.
    """
    if not isinstance(identity_registry, SQLiteAgentIdentityRegistry):
        raise TypeError("durable_identity_registry_required")
    if not isinstance(replay_guard, SQLiteAuthorizationReplayGuard):
        raise TypeError("durable_replay_guard_required")
    if not isinstance(agent_identity, AgentIdentity) or not agent_identity.is_well_formed():
        raise ValueError("valid_agent_identity_required")
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("key_id_required")
    if not isinstance(principal_id, str) or not principal_id.strip():
        raise ValueError("principal_id_required")
    if not callable(principal_agent_binding_verifier):
        raise TypeError("principal_agent_binding_verifier_required")
    if not isinstance(witness_namespace, str) or not witness_namespace.strip():
        raise ValueError("witness_namespace_required")
    try:
        witness_namespace_bytes = witness_namespace.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("invalid_witness_namespace_encoding") from None
    try:
        principal_id_bytes = principal_id.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("invalid_principal_id_encoding") from None
    try:
        key_id_bytes = key_id.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("invalid_key_id_encoding") from None
    try:
        agent_id_bytes = agent_identity.agent_id.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("invalid_agent_identity_encoding") from None
    if len(witness_namespace_bytes) > 512:
        raise ValueError("witness_namespace_too_long")
    if len(principal_id_bytes) > 256:
        raise ValueError("principal_id_too_long")
    if len(key_id_bytes) > 512:
        raise ValueError("key_id_too_long")
    if (isinstance(local_epoch, bool) or not isinstance(local_epoch, int)
            or not 0 <= local_epoch <= 0xFFFFFFFFFFFFFFFF):
        raise ValueError("invalid_local_witness_epoch")

    # Check external freshness before exposing a privileged trust chain.
    require_witness_epoch(
        witness, namespace=witness_namespace, local_epoch=local_epoch
    )

    if not identity_registry.is_trusted(agent_identity):
        raise PermissionError("durable_agent_identity_not_trusted")
    try:
        binding_valid = principal_agent_binding_verifier(
            principal_id, agent_identity.agent_id
        )
    except Exception:
        binding_valid = False
    if binding_valid is not True:
        raise PermissionError("principal_agent_binding_not_active")

    # A bounded, domain-separated challenge validates provider availability,
    # key ownership and signature correctness without exporting private bytes.
    challenge = (
        _BOOTSTRAP_DOMAIN
        + len(principal_id_bytes).to_bytes(4, "big")
        + principal_id_bytes
        + len(agent_id_bytes).to_bytes(4, "big")
        + agent_id_bytes
        + local_epoch.to_bytes(8, "big")
    )
    sign_for_identity(
        key_provider,
        key_id=key_id,
        identity=agent_identity,
        message=challenge,
    )

    chain = TrustChain(identity_registry, replay_guard)
    if chain.registry is not identity_registry or chain.replay_guard is not replay_guard:
        raise RuntimeError("durable_trust_dependency_binding_failed")

    return DurableTrustRuntime(
        trust_chain=chain,
        identity_registry=identity_registry,
        replay_guard=replay_guard,
        agent_identity=agent_identity,
        key_id=key_id,
        witness_namespace=witness_namespace,
        epoch=local_epoch,
    )
