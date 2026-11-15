"""Local Matrix supervisor orchestration contract.

This coordinates existing local reference components. It is not an OS sandbox:
the executor must enforce generation fencing and process isolation at the target.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from threading import RLock
from typing import Protocol

from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_core import NodeProfile, WorkloadRequest
from .matrix_grants import DurableGrantRegistry
from .matrix_membership_durable import DurableMembershipRegistry, MemberState
from .matrix_reservations import DurableReservationBook


class WorkloadExecutor(Protocol):
    """Adapter contract; implementations must enforce generation at the target."""

    def start(self, request: WorkloadRequest, generation: int) -> None: ...
    def stop(self, task_id: str, generation: int) -> None: ...


@dataclass(frozen=True)
class DispatchReceipt:
    task_id: str
    node_id: str
    grant_generation: int
    telemetry_age: float


@dataclass(frozen=True)
class RevocationResult:
    grant_generation: int
    cancelled_task_ids: tuple[str, ...]
    stop_failures: tuple[str, ...]


class MatrixSupervisor:
    """Fail-closed local admission, reservation, dispatch and revocation path.

    The membership/grant databases and reservation book must be provisioned for
    the same node. Telemetry timestamps and 'now' must use the same monotonic
    clock domain. Target-side fencing remains mandatory to close external races.
    """

    def __init__(
        self,
        node: NodeProfile,
        owner_id: str,
        membership: DurableMembershipRegistry,
        grants: DurableGrantRegistry,
        reservations: DurableReservationBook,
        device_policy: DeviceContributionPolicy,
        executor: WorkloadExecutor,
    ) -> None:
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id_required")
        if reservations.node.node_id != node.node_id:
            raise ValueError("reservation_book_node_mismatch")
        if reservations.node.grant != node.grant:
            raise ValueError("reservation_book_grant_mismatch")
        self.node = node
        self.owner_id = owner_id
        self.membership = membership
        self.grants = grants
        self.reservations = reservations
        self.device_policy = device_policy
        self.executor = executor
        self._active: dict[str, int] = {}
        self._lock = RLock()

    def _current_authority(self, request: WorkloadRequest):
        member = self.membership.get(self.node.node_id)
        if member is None or member.state is not MemberState.ACTIVE:
            raise PermissionError("node_membership_not_active")
        if member.owner_id != self.owner_id:
            raise PermissionError("node_owner_binding_mismatch")
        stored = self.grants.get(self.node.grant.grant_id)
        if stored is None:
            raise PermissionError("owner_grant_missing")
        if stored.node_id != self.node.node_id or stored.owner_id != self.owner_id:
            raise PermissionError("owner_grant_binding_mismatch")
        if stored.grant != self.node.grant:
            raise PermissionError("local_grant_snapshot_stale")
        if not stored.grant.enabled or request.generation != stored.grant.generation:
            raise PermissionError("owner_grant_disabled_or_stale")
        return member, stored

    def dispatch(
        self,
        request: WorkloadRequest,
        conditions: DeviceConditions,
        telemetry_captured_at: float,
        now: float,
        max_telemetry_age: float,
        estimated_duration_hours: float,
    ) -> DispatchReceipt:
        for name, value in (("now", now), ("telemetry_captured_at", telemetry_captured_at),
                            ("max_telemetry_age", max_telemetry_age)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(name + "_must_be_finite")
        if max_telemetry_age <= 0:
            raise ValueError("max_telemetry_age_must_be_positive")
        age = now - telemetry_captured_at
        if age < 0 or age > max_telemetry_age:
            raise PermissionError("device_telemetry_stale_or_from_future")

        with self._lock:
            self._current_authority(request)
            permitted, reason = self.device_policy.permits(conditions, estimated_duration_hours)
            if not permitted:
                raise PermissionError("device_contribution_policy_denied:" + reason)
            reservation = self.reservations.reserve(request)
            try:
                # Re-read the durable authority after reservation. Another
                # supervisor/process may have revoked the grant since the first
                # check; never dispatch from a stale local snapshot.
                self._current_authority(request)
                if reservation.grant_generation != request.generation:
                    raise PermissionError("reservation_generation_mismatch")
                # The target adapter must still enforce this generation
                # atomically; this second check narrows, but cannot close, the
                # cross-database/time-of-check race by itself.
                self.executor.start(request, reservation.grant_generation)
            except Exception:
                self.reservations.release(request.task_id)
                raise
            self._active[request.task_id] = reservation.grant_generation
            return DispatchReceipt(request.task_id, self.node.node_id,
                                   reservation.grant_generation, age)

    def revoke(self, expected_generation: int) -> RevocationResult:
        """Persist revocation first, clear reservations, then ask executor to stop.

        A failed stop is reported explicitly; it is never represented as a
        successful process termination. No new dispatch is admitted afterward.
        """
        with self._lock:
            revoked = self.grants.revoke(self.node.grant.grant_id, expected_generation)
            next_node = NodeProfile(
                self.node.node_id, self.node.failure_domain, self.node.attested,
                self.node.sandbox_ready, self.node.envelope, revoked.grant,
            )
            cancelled = self.reservations.reconcile_grant(next_node)
            self.node = next_node
            failures: list[str] = []
            for task_id in cancelled:
                generation = self._active.get(task_id, expected_generation)
                try:
                    self.executor.stop(task_id, generation)
                except Exception as exc:
                    failures.append(task_id + ":" + type(exc).__name__)
                else:
                    self._active.pop(task_id, None)
            return RevocationResult(revoked.grant.generation, cancelled, tuple(failures))
