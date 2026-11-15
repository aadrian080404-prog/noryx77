import pytest
from .matrix_core import (ContributionGrant, NodeProfile, ResourceEnvelope,
                          ResourceVector, WorkloadRequest)
from .matrix_reservations import DurableReservationBook


def node(generation=1, enabled=True):
    grant = ContributionGrant("grant", enabled, generation, ResourceVector(1500, 1_500_000),
                              frozenset({"compute"}))
    return NodeProfile("node-1", "rack-a", True, True,
        ResourceEnvelope(ResourceVector(4000, 4_000_000), ResourceVector(), ResourceVector(500, 500_000)),
        grant)


def request(task_id, cpu=500):
    return WorkloadRequest(task_id, "compute", ResourceVector(cpu, 500_000), 1)


def test_reservations_recover_after_restart_and_release(tmp_path):
    path = tmp_path / "reservations.db"
    book = DurableReservationBook(path, node())
    book.reserve(request("task-a"))
    reopened = DurableReservationBook(path, node())
    assert [r.task_id for r in reopened.list()] == ["task-a"]
    released = reopened.release("task-a")
    assert released.resources.cpu_milli == 500
    assert DurableReservationBook(path, node()).list() == ()


def test_reservations_enforce_aggregate_grant_and_resource_ceiling(tmp_path):
    book = DurableReservationBook(tmp_path / "reservations.db", node())
    book.reserve(request("task-a", 1000))
    with pytest.raises(PermissionError, match="owner_contribution_quota_exceeded"):
        book.reserve(request("task-b", 1000))


def test_reservations_are_atomic_across_independent_book_instances(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / "reservations.db"
    first = DurableReservationBook(path, node())
    second = DurableReservationBook(path, node())
    def attempt(index):
        try:
            (first if index % 2 else second).reserve(request(f"task-{index}", 500))
            return True
        except PermissionError:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(attempt, range(20)))
    assert sum(outcomes) == 3
    assert len(first.list()) == 3


def test_revocation_clears_persisted_reservations_and_rejects_stale_book(tmp_path):
    path = tmp_path / "reservations.db"
    book = DurableReservationBook(path, node())
    book.reserve(request("task-a"))
    new_node = node(generation=2, enabled=False)
    assert book.reconcile_grant(new_node) == ("task-a",)
    assert book.list() == ()
    with pytest.raises(PermissionError, match="node_not_eligible_for_workload"):
        book.reserve(request("task-b"))
    stale = DurableReservationBook.__new__(DurableReservationBook)
    stale.database, stale.timeout, stale.node = str(path), 5.0, node()
    with pytest.raises(PermissionError, match="durable_grant_generation_or_state_mismatch"):
        stale.reserve(request("stale-task"))


def _reserve_from_separate_process(path, index):
    book = DurableReservationBook(path, node())
    try:
        book.reserve(request(f"process-task-{index}", 500))
        return True
    except PermissionError:
        return False


def test_reservations_serialize_independent_processes(tmp_path):
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing
    path = str(tmp_path / "multi-process-reservations.db")
    DurableReservationBook(path, node())
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=8, mp_context=context) as pool:
        outcomes = list(pool.map(_reserve_from_separate_process, [path] * 16, range(16)))
    assert sum(outcomes) == 3
    assert len(DurableReservationBook(path, node()).list()) == 3
