import sqlite3

import pytest

from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_core import (
    ContributionGrant, NodeProfile, ResourceEnvelope, ResourceVector, WorkloadRequest,
)
from .matrix_grants import DurableGrantRegistry
from .matrix_membership_durable import AdmissionEvidence, DurableMembershipRegistry
from .matrix_reservations import DurableReservationBook
from .matrix_supervisor import MatrixSupervisor
from .matrix_target_fence import SQLiteGenerationFencedExecutor, TargetFenceError


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


def test_retry_pending_stops_does_not_stop_healthy_active_workloads(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)

    assert supervisor.retry_pending_stops() == ()
    assert executor.stopped == []
    assert [item.task_id for item in reservations.list()] == ["task-1"]


def test_retry_pending_stops_retries_only_failed_revocations(tmp_path):
    class SelectiveExecutor(FakeExecutor):
        def __init__(self):
            super().__init__(fail_stop={"task-1"})
            self.fail_first = True

        def stop(self, task_id, generation):
            if task_id == "task-1" and self.fail_first:
                self.fail_first = False
                raise RuntimeError("temporary_stop_failure")
            super().stop(task_id, generation)

    executor = SelectiveExecutor()
    supervisor, reservations, _ = _setup(tmp_path, executor)
    supervisor.dispatch(_request("task-1"), _conditions(), 100, 100, 2, 0.25)
    supervisor.dispatch(_request("task-2"), _conditions(), 100, 100, 2, 0.25)

    result = supervisor.revoke(expected_generation=1)
    assert result.stop_failures == ("task-1:RuntimeError",)
    assert executor.stopped == [("task-2", 1)]
    executor.fail_stop.clear()

    assert supervisor.retry_pending_stops() == ()
    assert executor.stopped == [("task-2", 1), ("task-1", 1)]
    assert supervisor.retry_pending_stops() == ()


def test_pending_stop_intent_survives_supervisor_restart(tmp_path):
    executor = FakeExecutor(fail_stop={"task-1"})
    supervisor, reservations, _ = _setup(tmp_path, executor)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    result = supervisor.revoke(expected_generation=1)
    assert result.stop_failures == ("task-1:RuntimeError",)
    intents = reservations.list_stop_intents()
    assert [(item.task_id, item.grant_generation, item.status) for item in intents] == [
        ("task-1", 1, "pending")
    ]

    reopened = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    restarted_executor = FakeExecutor()
    restarted = MatrixSupervisor(
        supervisor.node, "owner-1", supervisor.membership, supervisor.grants,
        reopened, _policy(), restarted_executor,
    )
    assert restarted.retry_pending_stops() == ()
    assert restarted_executor.stopped == [("task-1", 1)]
    assert reopened.list_stop_intents() == ()


def test_prepared_stop_intent_is_cancelled_if_grant_revocation_never_commits(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    reservations.prepare_stop_intents()
    recovered = reservations.recover_prepared_stop_intents(1, True)
    assert recovered == ()
    assert reservations.list_stop_intents() == ()


def test_prepared_stop_intent_recovers_if_grant_was_revoked_before_crash(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    reservations.prepare_stop_intents()
    revoked = supervisor.grants.revoke("grant-1", expected_generation=1)
    recovered = reservations.recover_prepared_stop_intents(revoked.grant.generation, False)
    assert [(item.task_id, item.status) for item in recovered] == [("task-1", "pending")]



def test_pending_stop_is_retried_when_acknowledgement_write_fails(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
    original_acknowledge = reservations.acknowledge_stop_intent
    failed_once = True

    def fail_first_acknowledgement(task_id, generation):
        nonlocal failed_once
        if failed_once:
            failed_once = False
            raise OSError("simulated_sqlite_acknowledgement_failure")
        return original_acknowledge(task_id, generation)

    reservations.acknowledge_stop_intent = fail_first_acknowledgement
    with pytest.raises(OSError, match="simulated_sqlite_acknowledgement_failure"):
        supervisor.revoke(expected_generation=1)

    assert executor.stopped == [("task-1", 1)]
    assert [(item.task_id, item.status) for item in reservations.list_stop_intents()] == [
        ("task-1", "pending")
    ]

    reservations.acknowledge_stop_intent = original_acknowledge
    assert supervisor.retry_pending_stops() == ()
    assert executor.stopped == [("task-1", 1), ("task-1", 1)]
    assert reservations.list_stop_intents() == ()


def test_prepared_revocation_fences_admission_across_supervisor_processes(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    supervisor.dispatch(_request("task-1"), _conditions(), 100, 100, 2, 0.25)

    # A second process has its own book/lock but shares the SQLite authority.
    second_process_book = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    reservations.prepare_stop_intents()
    with pytest.raises(PermissionError, match="durable_grant_generation_or_state_mismatch"):
        second_process_book.reserve(_request("task-2"))

    reservations.cancel_prepared_stop_intents()
    admitted = second_process_book.reserve(_request("task-2"))
    assert admitted.task_id == "task-2"


def test_failed_grant_revocation_keeps_admission_fenced_until_reconciliation(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    supervisor.dispatch(_request("task-1"), _conditions(), 100, 100, 2, 0.25)

    def fail_revoke(*_args, **_kwargs):
        raise RuntimeError("grant_store_unavailable")

    supervisor.grants.revoke = fail_revoke
    with pytest.raises(RuntimeError, match="grant_store_unavailable"):
        supervisor.revoke(expected_generation=1)

    second_process_book = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    with pytest.raises(PermissionError, match="durable_grant_generation_or_state_mismatch"):
        second_process_book.reserve(_request("task-2"))

    # Only an authoritative read proving that the old grant is still enabled
    # may clear the prepared intent and reopen admission.
    assert reservations.recover_prepared_stop_intents(1, True) == ()
    admitted = second_process_book.reserve(_request("task-2"))
    assert admitted.task_id == "task-2"


def test_ambiguous_revoke_commit_recovers_as_pending_stop_not_reopened(tmp_path):
    supervisor, reservations, executor = _setup(tmp_path)
    supervisor.dispatch(_request("task-1"), _conditions(), 100, 100, 2, 0.25)
    original_revoke = supervisor.grants.revoke

    def commit_then_lose_response(*args, **kwargs):
        original_revoke(*args, **kwargs)
        raise RuntimeError("grant_store_response_lost_after_commit")

    supervisor.grants.revoke = commit_then_lose_response
    with pytest.raises(RuntimeError, match="response_lost_after_commit"):
        supervisor.revoke(expected_generation=1)

    reopened = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    restarted = MatrixSupervisor(
        supervisor.node, "owner-1", supervisor.membership, supervisor.grants,
        reopened, _policy(), FakeExecutor(),
    )
    pending = reopened.list_stop_intents()
    assert [(item.task_id, item.status) for item in pending] == [("task-1", "pending")]
    with pytest.raises(PermissionError, match="durable_grant_generation_or_state_mismatch"):
        reopened.reserve(_request("task-2"))


def test_restart_reopens_admission_after_prepared_intent_without_reservations(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    reservations.prepare_stop_intents()

    reopened = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
    restarted = MatrixSupervisor(
        supervisor.node, "owner-1", supervisor.membership, supervisor.grants,
        reopened, _policy(), FakeExecutor(),
    )
    admitted = reopened.reserve(_request("task-after-recovery"))
    assert admitted.task_id == "task-after-recovery"



def test_prepare_stop_intents_fails_closed_if_durable_fence_row_is_missing_or_stale(tmp_path):
    supervisor, reservations, _ = _setup(tmp_path)
    supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)

    with sqlite3.connect(tmp_path / "reservations.db") as db:
        db.execute(
            "UPDATE matrix_reservation_state SET generation=99 WHERE node_id='node-1'"
        )

    with pytest.raises(PermissionError, match="durable_admission_fence_failed"):
        reservations.prepare_stop_intents()

    # The failed transaction must not create a prepared stop intent or silently
    # proceed with a revocation that has no durable admission fence.
    assert reservations.list_stop_intents() == ()

def test_supervisor_revocation_updates_target_fence_before_stop(tmp_path):
    underlying = FakeExecutor()
    target = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target-fence.db"), "node-1", underlying
    )
    try:
        supervisor, reservations, _ = _setup(tmp_path, target)
        supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
        assert underlying.started == [("task-1", 1)]

        result = supervisor.revoke(expected_generation=1)
        assert result.grant_generation == 2
        assert result.stop_failures == ()
        assert underlying.stopped == [("task-1", 1)]
        assert target.pending() == ()

        with pytest.raises(TargetFenceError, match="grant_not_active_for_generation"):
            target.start(_request(generation=1), 1)
    finally:
        target.close()

def test_external_grant_revocation_updates_target_fence_before_stale_dispatch_rejects(tmp_path):
    target = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target-fence.db"), "node-1", FakeExecutor()
    )
    try:
        supervisor, reservations, _ = _setup(tmp_path, target)
        original_reserve = reservations.reserve

        def reserve_then_revoke(request):
            reservation = original_reserve(request)
            supervisor.grants.revoke("grant-1", expected_generation=1)
            return reservation

        reservations.reserve = reserve_then_revoke
        with pytest.raises(PermissionError, match="local_grant_snapshot_stale"):
            supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)
        assert reservations.list() == ()
        with pytest.raises(TargetFenceError, match="grant_not_active_for_generation"):
            target.start(_request(generation=1), 1)
    finally:
        target.close()

def test_restart_recovers_crash_after_grant_commit_before_reservation_reconcile(tmp_path):
    underlying = FakeExecutor()
    target = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target-fence.db"), "node-1", underlying
    )
    try:
        supervisor, reservations, _ = _setup(tmp_path, target)
        supervisor.dispatch(_request(), _conditions(), 100, 100, 2, 0.25)

        # Simulate a crash after durable admission fencing and grant revocation,
        # but before MatrixSupervisor can reconcile reservations or stop tasks.
        reservations.prepare_stop_intents()
        supervisor.grants.revoke("grant-1", expected_generation=1)

        reopened = DurableReservationBook(tmp_path / "reservations.db", supervisor.node)
        restarted = MatrixSupervisor(
            supervisor.node, "owner-1", supervisor.membership, supervisor.grants,
            reopened, _policy(), target,
        )
        assert restarted.node.grant.generation == 2
        assert restarted.retry_pending_stops() == ()
        assert underlying.stopped == [("task-1", 1)]
        assert reopened.list() == ()
        assert target.pending() == ()
    finally:
        target.close()
