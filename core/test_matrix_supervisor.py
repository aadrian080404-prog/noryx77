import pytest

from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_core import (
    ContributionGrant, NodeProfile, ResourceEnvelope, ResourceVector, WorkloadRequest,
)
from .matrix_grants import DurableGrantRegistry
from .matrix_membership_durable import AdmissionEvidence, DurableMembershipRegistry
from .matrix_reservations import DurableReservationBook
from .matrix_supervisor import MatrixSupervisor


def _grant(enabled=True, generation=1):
    return ContributionGrant(
        "grant-1", enabled, generation, ResourceVector(1500, 2_000_000),
        frozenset({"compute"}), False,
    )


def _node(grant):
    return NodeProfile(
        "node-1", "rack-a", True, True,
        ResourceEnvelope(ResourceVector(4000, 4_000_000), ResourceVector(), ResourceVector(500, 500_000)),
        grant,
    )


def _conditions():
    return DeviceConditions(90, 35, 2, 100, 100)


def _policy():
    return DeviceContributionPolicy(True, 30, 42, 4, 1000, 10, ((0, 1000),))


def _request(task="task-1", generation=1):
    return WorkloadRequest(task, "compute", ResourceVector(500, 500_000), generation)


class FakeExecutor:
    def __init__(self, fail_start=False, fail_stop=()):
        self.started = []
        self.stopped = []
        self.fail_start = fail_start
        self.fail_stop = set(fail_stop)

    def start(self, request, generation):
        if self.fail_start:
            raise RuntimeError("executor_start_failed")
        self.started.append((request.task_id, generation))

    def stop(self, task_id, generation):
        if task_id in self.fail_stop:
            raise RuntimeError("executor_stop_failed")
        self.stopped.append((task_id, generation))


def _setup(tmp_path, executor=None):
    grant = _grant()
    node = _node(grant)
    membership = DurableMembershipRegistry(tmp_path / "membership.db")
    evidence = AdmissionEvidence(
        "node-1", "owner-1", "rack-a", "sha256:measurement", 1, "nonce-1",
        frozenset({"compute"}),
    )
    membership.admit(evidence, b"proof", lambda _e, proof: proof == b"proof")
    grants = DurableGrantRegistry(tmp_path / "grants.db")
    grants.put("node-1", "owner-1", grant)
    reservations = DurableReservationBook(tmp_path / "reservations.db", node)
    executor = executor or FakeExecutor()
    supervisor = MatrixSupervisor(
        node, "owner-1", membership, grants, reservations, _policy(), executor,
    )
    return supervisor, reservations, executor


def test_dispatch_checks_membership_grant_budget_and_fresh_telemetry(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    receipt = supervisor.dispatch(_request(), _conditions(), 99.5, 100, 2, 0.25)
    assert receipt.task_id == "task-1"
    assert receipt.grant_generation == 1
    assert receipt.telemetry_age == 0.5
    assert executor.started == [("task-1", 1)]
    assert [item.task_id for item in reservations.list()] == ["task-1"]


@pytest.mark.parametrize("captured,now", [(90, 100), (101, 100)])
def test_dispatch_rejects_stale_or_future_telemetry_without_reserving(tmp_path, captured, now):
    supervisor, reservations, executor = _setup(tmp_path)
    with pytest.raises(PermissionError, match="device_telemetry_stale_or_from_future"):
        supervisor.dispatch(_request(), _conditions(), captured, now, 2, 0.25)
    assert reservations.list() == ()
    assert executor.started == []


def test_executor_start_failure_releases_reservation(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path, FakeExecutor(fail_start=True))
    with pytest.raises(RuntimeError, match="executor_start_failed"):
        supervisor.dispatch(_request(), _conditions(), 99, 100, 2, 0.25)
    assert reservations.list() == ()


def test_dispatch_rechecks_durable_grant_after_reservation(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    original_reserve = reservations.reserve

    def reserve_then_revoke(request):
        reservation = original_reserve(request)
        supervisor.grants.revoke("grant-1", expected_generation=1)
        return reservation

    reservations.reserve = reserve_then_revoke
    with pytest.raises(PermissionError, match="local_grant_snapshot_stale"):
        supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    assert reservations.list() == ()
    assert executor.started == []


def test_dispatch_fails_closed_when_membership_is_revoked(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.membership.revoke("node-1", 2)
    with pytest.raises(PermissionError, match="node_membership_not_active"):
        supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    assert reservations.list() == ()
    assert executor.started == []


def test_owner_revocation_clears_reservations_before_executor_drain(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    result = supervisor.revoke(expected_generation=1)
    assert result.grant_generation == 2
    assert result.cancelled_task_ids == ("task-1",)
    assert result.stop_failures == ()
    assert reservations.list() == ()
    assert executor.stopped == [("task-1", 1)]
    with pytest.raises(PermissionError):
        supervisor.dispatch(_request(generation=2), _conditions(), 100, 100, 2, 0.25)


def test_stop_failure_is_reported_not_claimed_as_terminated(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path, FakeExecutor(fail_stop={"task-1"}))
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    result = supervisor.revoke(expected_generation=1)
    assert result.cancelled_task_ids == ("task-1",)
    assert result.stop_failures == ("task-1:RuntimeError",)
    assert reservations.list() == ()
    assert executor.stopped == []


def test_pending_stop_can_be_retried_after_transient_executor_failure(tmp_path):
    class FlakyExecutor(FakeExecutor):
        def __init__(self):
            super().__init__()
            self.fail_once = True

        def stop(self, task_id, generation):
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError("temporary_stop_failure")
            super().stop(task_id, generation)

    executor = FlakyExecutor()
    supervisor, reservations, _ = _setup(tmp_path, executor)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    result = supervisor.revoke(expected_generation=1)
    assert result.stop_failures == ("task-1:RuntimeError",)
    assert reservations.list() == ()
    assert supervisor.retry_pending_stops() == ()
    assert executor.stopped == [("task-1", 1)]
    assert supervisor.retry_pending_stops() == ()


def test_supervisor_restart_rehydrates_active_tasks_for_revocation(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)

    reopened = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    restarted_executor = FakeExecutor()
    restarted = MatrixSupervisor(
        supervisor.node, "owner-1", supervisor.membership, supervisor.grants,
        reopened, _policy(), restarted_executor,
    )
    result = restarted.revoke(expected_generation=1)
    assert result.cancelled_task_ids == ("task-1",)
    assert result.stop_failures == ()
    assert reopened.list() == ()
    assert restarted_executor.stopped == [("task-1", 1)]
    assert executor.stopped == []
