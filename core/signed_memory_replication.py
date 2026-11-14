"""Identity-authenticated replication batches for distributed memory."""
from __future__ import annotations

from dataclasses import dataclass
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .distributed_memory import (
    MAX_BATCH_EVENTS,
    MAX_MEMORY_VALUE,
    DistributedMemoryStore,
    MemoryEvent,
)
from .identity import (
    AgentAttestation,
    AgentIdentity,
    AgentIdentityAuthority,
    IdentityRegistry,
)

MAX_SIGNED_BATCH_EVENTS = 256
MAX_SIGNED_BATCH_BYTES = 4 * 1024 * 1024
_DOMAIN = b"NORYX7/SIGNED_MEMORY_BATCH/v1\x00"


def _event_payload(event: MemoryEvent) -> dict[str, object]:
    event.validate()
    return {
        "actor_id": event.actor_id,
        "counter": event.counter,
        "key": event.key,
        "value": event.value,
        "deleted": event.deleted,
        "clock": [[actor, counter] for actor, counter in event.clock],
    }


def _statement(events: tuple[MemoryEvent, ...]) -> bytes:
    if not isinstance(events, tuple) or not 1 <= len(events) <= MAX_SIGNED_BATCH_EVENTS:
        raise ValueError("signed_memory_batch_size_invalid")
    payload = [_event_payload(event) for event in events]
    encoded = _DOMAIN + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if len(encoded) > MAX_SIGNED_BATCH_BYTES:
        raise ValueError("signed_memory_batch_bytes_exceeded")
    return encoded


@dataclass(frozen=True)
class SignedMemoryBatch:
    attestation: AgentAttestation
    events: tuple[MemoryEvent, ...]


def sign_memory_batch(
    identity: AgentIdentity,
    private_key: Ed25519PrivateKey,
    events: tuple[MemoryEvent, ...],
) -> SignedMemoryBatch:
    if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
        raise ValueError("signed_memory_identity_invalid")
    if any(event.actor_id != identity.agent_id for event in events):
        raise ValueError("memory_batch_actor_identity_mismatch")
    ordered = tuple(sorted(events, key=lambda event: (event.actor_id, event.counter)))
    if len({_event_payload(event)["counter"] for event in ordered}) != len(ordered):
        raise ValueError("duplicate_memory_batch_counter")
    statement = _statement(ordered)
    attestation = AgentIdentityAuthority.sign(identity, private_key, statement)
    return SignedMemoryBatch(attestation, ordered)


def verify_and_merge_memory_batch(
    store: DistributedMemoryStore,
    batch: SignedMemoryBatch,
    registry: IdentityRegistry,
) -> int:
    if not isinstance(store, DistributedMemoryStore):
        raise TypeError("distributed_memory_store_required")
    if not isinstance(batch, SignedMemoryBatch) or not isinstance(batch.attestation, AgentAttestation):
        raise ValueError("signed_memory_batch_required")
    if not isinstance(registry, IdentityRegistry):
        raise TypeError("identity_registry_required")
    identity = batch.attestation.identity
    if not identity.is_well_formed() or any(
        event.actor_id != identity.agent_id for event in batch.events
    ):
        raise PermissionError("memory_batch_sender_identity_mismatch")
    statement = _statement(batch.events)
    if batch.attestation.statement != statement:
        raise PermissionError("memory_batch_statement_mismatch")

    # Keep signature verification and bounded local merge within the trust
    # registry's revocation critical section. No network or agent code runs here.
    def verify_and_apply(trusted: AgentIdentity) -> int:
        if trusted != identity or not AgentIdentityAuthority.verify(batch.attestation):
            raise PermissionError("memory_batch_signature_or_trust_invalid")
        return store.merge(batch.events)

    return registry.with_trusted_identity(identity.agent_id, verify_and_apply)
