"""NORYX7 Matrix Core: opt-in resource leases and bounded local reservations.

This is a deterministic policy primitive, not a distributed scheduler or sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceKind(str, Enum):
    CPU_MILLI = "cpu_milli"
    MEMORY_BYTES = "memory_bytes"
    STORAGE_BYTES = "storage_bytes"
    BANDWIDTH_BPS = "bandwidth_bps"


@dataclass(frozen=True)
class ResourceVector:
    cpu_milli: int = 0
    memory_bytes: int = 0
    storage_bytes: int = 0
    bandwidth_bps: int = 0

    def __post_init__(self) -> None:
        for value in (self.cpu_milli, self.memory_bytes, self.storage_bytes, self.bandwidth_bps):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("resource_vector_values_must_be_nonnegative_integers")

    def fits_within(self, other: "ResourceVector") -> bool:
        return (
            self.cpu_milli <= other.cpu_milli
            and self.memory_bytes <= other.memory_bytes
            and self.storage_bytes <= other.storage_bytes
            and self.bandwidth_bps <= other.bandwidth_bps
        )

    def __add__(self, other: "ResourceVector") -> "ResourceVector":
        return ResourceVector(
            self.cpu_milli + other.cpu_milli,
            self.memory_bytes + other.memory_bytes,
            self.storage_bytes + other.storage_bytes,
            self.bandwidth_bps + other.bandwidth_bps,
        )

    def __sub__(self, other: "ResourceVector") -> "ResourceVector":
        values = (
            self.cpu_milli - other.cpu_milli,
            self.memory_bytes - other.memory_bytes,
            self.storage_bytes - other.storage_bytes,
            self.bandwidth_bps - other.bandwidth_bps,
        )
        if any(value < 0 for value in values):
            raise ValueError("resource_vector_underflow")
        return ResourceVector(*values)


@dataclass(frozen=True)
class ResourceEnvelope:
    capacity: ResourceVector
    committed: ResourceVector
    reserve: ResourceVector

    def __post_init__(self) -> None:
        if not self.committed.fits_within(self.capacity):
            raise ValueError("committed_exceeds_capacity")
        if not self.reserve.fits_within(self.capacity - self.committed):
            raise ValueError("reserve_exceeds_uncommitted_capacity")

    @property
    def allocatable(self) -> ResourceVector:
        return self.capacity - self.committed - self.reserve

    def can_reserve(self, request: ResourceVector) -> bool:
        return request.fits_within(self.allocatable)

    def reserve_work(self, request: ResourceVector) -> "ResourceEnvelope":
        if not self.can_reserve(request):
            raise ValueError("resource_reserve_unavailable")
        return ResourceEnvelope(self.capacity, self.committed + request, self.reserve)

    def release_work(self, request: ResourceVector) -> "ResourceEnvelope":
        return ResourceEnvelope(self.capacity, self.committed - request, self.reserve)


@dataclass(frozen=True)
class ContributionGrant:
    """User/domain consent for a bounded resource contribution; disabled by default."""

    grant_id: str
    enabled: bool = False
    generation: int = 0
    max_resources: ResourceVector = ResourceVector()
    allowed_workloads: frozenset[str] = frozenset()
    allow_user_data: bool = False

    def __post_init__(self) -> None:
        if not self.grant_id.strip():
            raise ValueError("grant_id_required")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 0:
            raise ValueError("invalid_grant_generation")
        if not isinstance(self.enabled, bool) or not isinstance(self.allow_user_data, bool):
            raise ValueError("grant_flags_must_be_boolean")
        if any(not isinstance(item, str) or not item.strip() for item in self.allowed_workloads):
            raise ValueError("invalid_workload_class")


@dataclass(frozen=True)
class NodeProfile:
    node_id: str
    failure_domain: str
    attested: bool
    sandbox_ready: bool
    envelope: ResourceEnvelope
    grant: ContributionGrant

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.failure_domain.strip():
            raise ValueError("node_identity_and_failure_domain_required")
        if not isinstance(self.attested, bool) or not isinstance(self.sandbox_ready, bool):
            raise ValueError("node_security_flags_must_be_boolean")


@dataclass(frozen=True)
class WorkloadRequest:
    task_id: str
    workload_class: str
    resources: ResourceVector
    generation: int
    requires_attestation: bool = True
    requires_sandbox: bool = True
    requires_user_data: bool = False
    allowed_failure_domains: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.workload_class.strip():
            raise ValueError("task_and_workload_class_required")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 0:
            raise ValueError("invalid_workload_generation")
        if not isinstance(self.requires_attestation, bool) or not isinstance(self.requires_sandbox, bool):
            raise ValueError("security_requirements_must_be_boolean")
        if not isinstance(self.requires_user_data, bool):
            raise ValueError("data_access_requirement_must_be_boolean")


def eligible(node: NodeProfile, request: WorkloadRequest) -> bool:
    """Return whether this node may accept the request under its current grant."""
    grant = node.grant
    if not grant.enabled or request.generation != grant.generation:
        return False
    if request.workload_class not in grant.allowed_workloads:
        return False
    if request.requires_user_data and not grant.allow_user_data:
        return False
    if request.requires_attestation and not node.attested:
        return False
    if request.requires_sandbox and not node.sandbox_ready:
        return False
    if request.allowed_failure_domains and node.failure_domain not in request.allowed_failure_domains:
        return False
    if not request.resources.fits_within(grant.max_resources):
        return False
    return node.envelope.can_reserve(request.resources)


class LocalReservationBook:
    """Single-process, node-local reservation book.

    The caller must serialize access in a multi-threaded runtime. Persistence,
    distributed consensus, process fencing and sandbox enforcement are separate.
    """

    def __init__(self, node: NodeProfile) -> None:
        self._node = node
        self._reservations: dict[str, ResourceVector] = {}

    @property
    def node(self) -> NodeProfile:
        return self._node

    def reserve(self, request: WorkloadRequest) -> NodeProfile:
        if request.task_id in self._reservations:
            raise ValueError("task_already_reserved")
        if not eligible(self._node, request):
            raise PermissionError("node_not_eligible_for_workload")
        envelope = self._node.envelope.reserve_work(request.resources)
        self._node = NodeProfile(
            self._node.node_id, self._node.failure_domain, self._node.attested,
            self._node.sandbox_ready, envelope, self._node.grant,
        )
        self._reservations[request.task_id] = request.resources
        return self._node

    def release(self, task_id: str) -> NodeProfile:
        resources = self._reservations.pop(task_id, None)
        if resources is None:
            raise KeyError("unknown_reservation")
        envelope = self._node.envelope.release_work(resources)
        self._node = NodeProfile(
            self._node.node_id, self._node.failure_domain, self._node.attested,
            self._node.sandbox_ready, envelope, self._node.grant,
        )
        return self._node

    def revoke(self, new_grant: ContributionGrant) -> tuple[str, ...]:
        """Apply a newer grant generation; old reservations are reported for drain.

        A production supervisor must terminate or safely drain these tasks. This
        primitive deliberately does not pretend to kill external processes.
        """
        if new_grant.grant_id != self._node.grant.grant_id:
            raise ValueError("grant_identity_mismatch")
        if new_grant.generation <= self._node.grant.generation:
            raise ValueError("grant_generation_must_increase")
        cancelled = tuple(sorted(self._reservations))
        self._reservations.clear()
        envelope = ResourceEnvelope(
            self._node.envelope.capacity,
            self._node.envelope.committed,
            self._node.envelope.reserve,
        )
        # Existing work must be released before new grant takes effect.
        released = envelope
        for resources in self._reservations.values():
            released = released.release_work(resources)
        self._node = NodeProfile(
            self._node.node_id, self._node.failure_domain, self._node.attested,
            self._node.sandbox_ready, released, new_grant,
        )
        return cancelled
