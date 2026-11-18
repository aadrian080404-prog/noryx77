"""NORYX7 Continuity Protocol: authenticated node fencing and controlled rejoin.

This module is a local policy primitive, not a network protocol or consensus
implementation. Deployments must supply cryptographic attestation verification,
human/authority rejoin approval, and a durable audit sink.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from enum import Enum
from functools import wraps
from threading import RLock
from typing import Callable, Mapping

from .identity import AgentAttestation, AgentIdentity, AgentIdentityAuthority, IdentityRegistry


MAX_NODE_ID_BYTES = 256
MAX_CAPABILITIES = 64


class NodeContinuityState(str, Enum):
    ACTIVE = "active"
    ISOLATED = "isolated"


@dataclass(frozen=True)
class NodeContinuityRecord:
    node_id: str
    identity_fingerprint: str
    generation: int
    sequence: int
    capabilities: tuple[str, ...]
    state: NodeContinuityState


AttestationVerifier = Callable[..., bool]
RejoinApprover = Callable[..., bool]
AuditSink = Callable[[str, Mapping[str, object]], None]


def _synchronized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


class ContinuitySupervisor:
    """Fences stale/untrusted nodes and requires explicit approval to rejoin.

    The verifier must validate an attestation bound to every supplied field.
    The supervisor deliberately does not implement cryptography, networking,
    remote consensus, or human approval itself.
    """

    def __init__(
        self,
        *,
        verify_attestation: AttestationVerifier,
        approve_rejoin: RejoinApprover,
        audit: AuditSink,
        max_nodes: int = 1024,
        state_store: object | None = None,
    ) -> None:
        if not callable(verify_attestation) or not callable(approve_rejoin) or not callable(audit):
            raise TypeError("continuity_security_dependencies_required")
        if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or not 1 <= max_nodes <= 65_536:
            raise ValueError("invalid_continuity_capacity")
        self._verify_attestation = verify_attestation
        self._approve_rejoin = approve_rejoin
        self._audit = audit
        self._max_nodes = max_nodes
        self._state_store = state_store
        self._nodes: dict[str, NodeContinuityRecord] = {}
        self._lock = RLock()
        if state_store is not None:
            if not all(callable(getattr(state_store, name, None)) for name in (
                "load_records", "insert_record", "replace_record"
            )):
                raise TypeError("continuity_state_store_contract_required")
            restored = state_store.load_records()
            if not isinstance(restored, (tuple, list)) or len(restored) > max_nodes:
                raise RuntimeError("continuity_state_store_invalid")
            for record in restored:
                if not isinstance(record, NodeContinuityRecord) or record.node_id in self._nodes:
                    raise RuntimeError("continuity_state_store_invalid")
                self._validate_identity(record.node_id, record.identity_fingerprint, record.capabilities)
                if (
                    isinstance(record.generation, bool) or not isinstance(record.generation, int) or record.generation < 0
                    or isinstance(record.sequence, bool) or not isinstance(record.sequence, int) or record.sequence < 0
                    or not isinstance(record.state, NodeContinuityState)
                ):
                    raise RuntimeError("continuity_state_store_invalid")
                self._nodes[record.node_id] = record

    def _persist_insert(self, record: NodeContinuityRecord) -> None:
        if self._state_store is not None:
            self._state_store.insert_record(record)

    def _persist_replace(self, previous: NodeContinuityRecord, replacement: NodeContinuityRecord) -> None:
        if self._state_store is not None and self._state_store.replace_record(previous, replacement) is not True:
            raise RuntimeError("continuity_state_store_conflict")

    @staticmethod
    def _validate_identity(node_id: str, fingerprint: str, capabilities: tuple[str, ...]) -> None:
        if not isinstance(node_id, str) or not node_id.strip() or len(node_id.encode("utf-8")) > MAX_NODE_ID_BYTES:
            raise ValueError("invalid_node_id")
        if (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in fingerprint)
        ):
            raise ValueError("invalid_identity_fingerprint")
        if (
            not isinstance(capabilities, tuple)
            or not 1 <= len(capabilities) <= MAX_CAPABILITIES
            or any(not isinstance(item, str) or not item.strip() for item in capabilities)
            or len(set(capabilities)) != len(capabilities)
        ):
            raise ValueError("invalid_node_capabilities")

    def _attested(
        self, *, node_id: str, identity_fingerprint: str, generation: int,
        sequence: int, attestation: object,
    ) -> bool:
        try:
            return self._verify_attestation(
                node_id=node_id,
                identity_fingerprint=identity_fingerprint,
                generation=generation,
                sequence=sequence,
                attestation=attestation,
            ) is True
        except Exception:
            return False

    def _emit(self, event: str, **payload: object) -> None:
        self._audit(event, payload)

    @_synchronized
    def register(
        self, *, node_id: str, identity_fingerprint: str,
        capabilities: tuple[str, ...], attestation: object,
    ) -> NodeContinuityRecord:
        self._validate_identity(node_id, identity_fingerprint, capabilities)
        if node_id in self._nodes:
            raise ValueError("node_already_registered")
        if len(self._nodes) >= self._max_nodes:
            raise OverflowError("continuity_node_capacity_exceeded")
        if not self._attested(
            node_id=node_id, identity_fingerprint=identity_fingerprint,
            generation=0, sequence=0, attestation=attestation,
        ):
            raise PermissionError("node_attestation_rejected")
        record = NodeContinuityRecord(
            node_id, identity_fingerprint, 0, 0, capabilities, NodeContinuityState.ACTIVE
        )
        self._emit("continuity_node_registered", node_id=node_id, generation=0)
        self._persist_insert(record)
        self._nodes[node_id] = record
        return record

    @_synchronized
    def heartbeat(
        self, *, node_id: str, generation: int, sequence: int, attestation: object,
    ) -> NodeContinuityRecord:
        current = self._nodes.get(node_id)
        if current is None:
            raise LookupError("unknown_continuity_node")
        valid_counters = (
            isinstance(generation, int) and not isinstance(generation, bool)
            and isinstance(sequence, int) and not isinstance(sequence, bool)
            and generation == current.generation and sequence > current.sequence
        )
        trusted = valid_counters and current.state is NodeContinuityState.ACTIVE and self._attested(
            node_id=node_id,
            identity_fingerprint=current.identity_fingerprint,
            generation=generation,
            sequence=sequence,
            attestation=attestation,
        )
        if not trusted:
            isolated = NodeContinuityRecord(
                current.node_id, current.identity_fingerprint, current.generation,
                current.sequence, current.capabilities, NodeContinuityState.ISOLATED,
            )
            self._nodes[node_id] = isolated
            self._emit(
                "continuity_node_isolated", node_id=node_id,
                generation=current.generation, last_sequence=current.sequence,
                reason="stale_or_invalid_heartbeat",
            )
            self._persist_replace(current, isolated)
            raise PermissionError("node_heartbeat_rejected")
        updated = NodeContinuityRecord(
            current.node_id, current.identity_fingerprint, current.generation,
            sequence, current.capabilities, NodeContinuityState.ACTIVE,
        )
        try:
            self._emit("continuity_node_heartbeat", node_id=node_id, sequence=sequence)
        except Exception:
            isolated = NodeContinuityRecord(
                current.node_id, current.identity_fingerprint, current.generation,
                current.sequence, current.capabilities, NodeContinuityState.ISOLATED,
            )
            self._nodes[node_id] = isolated
            try:
                self._persist_replace(current, isolated)
            except Exception:
                pass
            raise
        self._persist_replace(current, updated)
        self._nodes[node_id] = updated
        return updated

    @_synchronized
    def isolate(self, node_id: str, *, reason: str) -> NodeContinuityRecord:
        current = self._nodes.get(node_id)
        if current is None:
            raise LookupError("unknown_continuity_node")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 256:
            raise ValueError("invalid_isolation_reason")
        isolated = NodeContinuityRecord(
            current.node_id, current.identity_fingerprint, current.generation,
            current.sequence, current.capabilities, NodeContinuityState.ISOLATED,
        )
        self._emit("continuity_node_isolated", node_id=node_id, reason=reason)
        self._persist_replace(current, isolated)
        self._nodes[node_id] = isolated
        return isolated

    @_synchronized
    def rejoin(
        self, *, node_id: str, generation: int, sequence: int,
        attestation: object, approval: object,
    ) -> NodeContinuityRecord:
        current = self._nodes.get(node_id)
        if current is None:
            raise LookupError("unknown_continuity_node")
        if current.state is not NodeContinuityState.ISOLATED:
            raise PermissionError("node_is_not_isolated")
        if (
            isinstance(generation, bool) or not isinstance(generation, int)
            or generation <= current.generation
            or isinstance(sequence, bool) or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise PermissionError("node_rejoin_fence_rejected")
        if not self._attested(
            node_id=node_id, identity_fingerprint=current.identity_fingerprint,
            generation=generation, sequence=sequence, attestation=attestation,
        ):
            raise PermissionError("node_rejoin_attestation_rejected")
        try:
            approved = self._approve_rejoin(
                node_id=node_id, previous_generation=current.generation,
                new_generation=generation, approval=approval,
            ) is True
        except Exception:
            approved = False
        if not approved:
            raise PermissionError("node_rejoin_approval_required")
        updated = NodeContinuityRecord(
            current.node_id, current.identity_fingerprint, generation,
            sequence, current.capabilities, NodeContinuityState.ACTIVE,
        )
        self._emit("continuity_node_rejoined", node_id=node_id, generation=generation)
        self._persist_replace(current, updated)
        self._nodes[node_id] = updated
        return updated

    @_synchronized
    def resolve_all(self, capability: str) -> tuple[NodeContinuityRecord, ...]:
        """Return all active nodes for a capability in deterministic node-ID order."""
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability_required")
        return tuple(
            node for node in sorted(self._nodes.values(), key=lambda item: item.node_id)
            if node.state is NodeContinuityState.ACTIVE and capability in node.capabilities
        )

    @_synchronized
    def resolve(self, capability: str) -> NodeContinuityRecord:
        candidates = self.resolve_all(capability)
        if not candidates:
            raise LookupError("no_trusted_active_node")
        return candidates[0]

    @_synchronized
    def snapshot(self) -> tuple[NodeContinuityRecord, ...]:
        return tuple(self._nodes[key] for key in sorted(self._nodes))



def node_attestation_statement(
    *, node_id: str, identity_fingerprint: str, generation: int, sequence: int,
) -> bytes:
    """Canonical, domain-separated statement signed by an NORYX7 node identity."""
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("invalid_node_id")
    if (
        not isinstance(identity_fingerprint, str)
        or len(identity_fingerprint) != 64
        or any(char not in "0123456789abcdef" for char in identity_fingerprint)
    ):
        raise ValueError("invalid_identity_fingerprint")
    if (
        isinstance(generation, bool) or not isinstance(generation, int) or generation < 0
        or isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0
    ):
        raise ValueError("invalid_node_attestation_counters")
    payload = {
        "domain": "noryx7/node-continuity-attestation/v1",
        "node_id": node_id,
        "identity_fingerprint": identity_fingerprint,
        "generation": generation,
        "sequence": sequence,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def agent_identity_attestation_verifier(registry: IdentityRegistry) -> AttestationVerifier:
    """Adapt the existing Ed25519 identity registry to NCP's attestation contract.

    The registry's short trusted-identity critical section covers only key
    comparison and signature verification. It performs no external I/O.
    """
    if not isinstance(registry, IdentityRegistry):
        raise TypeError("identity_registry_required")

    def verify(
        *, node_id: str, identity_fingerprint: str, generation: int,
        sequence: int, attestation: object,
    ) -> bool:
        if not isinstance(attestation, AgentAttestation):
            return False
        identity = attestation.identity
        if (
            identity.agent_id != node_id
            or hashlib.sha256(identity.public_key).hexdigest() != identity_fingerprint
        ):
            return False
        try:
            expected_statement = node_attestation_statement(
                node_id=node_id,
                identity_fingerprint=identity_fingerprint,
                generation=generation,
                sequence=sequence,
            )
            if attestation.statement != expected_statement:
                return False
            return registry.with_trusted_identity(
                node_id,
                lambda trusted: (
                    trusted == identity and AgentIdentityAuthority.verify(attestation)
                ),
            ) is True
        except Exception:
            return False

    return verify



def audit_log_sink(audit_log: object) -> AuditSink:
    """Adapt the native AuditLog.record(event, **fields) contract to NCP."""
    recorder = getattr(audit_log, "record", None)
    if not callable(recorder):
        raise TypeError("audit_log_recorder_required")

    def record(event: str, payload: Mapping[str, object]) -> None:
        if not isinstance(payload, Mapping):
            raise ValueError("invalid_continuity_audit_payload")
        recorder(event, **dict(payload))

    return record
