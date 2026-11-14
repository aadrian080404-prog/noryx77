import pytest

from core.distributed_memory import DistributedMemoryStore, MemoryEvent


def test_merge_rejects_actor_counter_gap_atomically(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    first = MemoryEvent("peer", 1, "a", "one", False, (("peer", 1),))
    third = MemoryEvent("peer", 3, "c", "three", False, (("peer", 3),))
    with pytest.raises(ValueError, match="counter_gap"):
        target.merge((first, third))
    assert target.vector_clock() == {}
    assert target.read("a") is None
    target.close()


def test_merge_accepts_contiguous_events_and_idempotent_replay(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    first = MemoryEvent("peer", 1, "a", "one", False, (("peer", 1),))
    second = MemoryEvent("peer", 2, "b", "two", False, (("peer", 2),))
    assert target.merge((second, first)) == 2
    assert target.merge((first, second)) == 0
    assert target.vector_clock() == {"peer": 2}
    target.close()


def test_merge_rejects_missing_middle_event_after_existing_prefix(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    first = MemoryEvent("peer", 1, "a", "one", False, (("peer", 1),))
    third = MemoryEvent("peer", 3, "c", "three", False, (("peer", 3),))
    assert target.merge((first,)) == 1
    with pytest.raises(ValueError, match="counter_gap"):
        target.merge((third,))
    assert target.vector_clock() == {"peer": 1}
    target.close()


def test_merge_rejects_missing_cross_actor_vector_dependency_atomically(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    dependent = MemoryEvent(
        "peer-a", 1, "derived", "depends on peer-b/1", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    with pytest.raises(ValueError, match="causal_dependency_missing"):
        target.merge((dependent,))
    assert target.vector_clock() == {}
    assert target.read("derived") is None
    target.close()


def test_merge_resolves_cross_actor_dependencies_inside_batch(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    dependency = MemoryEvent("peer-b", 1, "source", "base", False, (("peer-b", 1),))
    dependent = MemoryEvent(
        "peer-a", 1, "derived", "computed", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    assert target.merge((dependent, dependency)) == 2
    assert target.vector_clock() == {"peer-a": 1, "peer-b": 1}
    assert target.read("derived") == dependent
    target.close()


def test_merge_rejects_missing_middle_cross_actor_dependency(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    first = MemoryEvent("peer-b", 1, "b1", "one", False, (("peer-b", 1),))
    second = MemoryEvent("peer-b", 2, "b2", "two", False, (("peer-b", 2),))
    dependent = MemoryEvent(
        "peer-a", 1, "derived", "computed", False,
        (("peer-a", 1), ("peer-b", 2)),
    )
    with pytest.raises(ValueError, match="causal_dependency_missing"):
        target.merge((first, dependent))
    assert target.vector_clock() == {}
    assert target.read("b1") is None
    target.close()


def test_merge_preserves_actor_gap_error_for_missing_counter(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    third = MemoryEvent("peer", 3, "c", "three", False, (("peer", 3),))
    with pytest.raises(ValueError, match="counter_gap"):
        target.merge((third,))
    assert target.vector_clock() == {}
    target.close()


def test_startup_rejects_legacy_database_with_missing_causal_history(tmp_path):
    path = str(tmp_path / "legacy-memory.sqlite")
    store = DistributedMemoryStore(path, actor_id="receiver")
    legacy_event = MemoryEvent(
        "peer-a", 1, "derived", "depends on missing peer-b/1", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    store._db.execute("BEGIN IMMEDIATE")
    store._insert_event(legacy_event)
    store._db.execute("COMMIT")
    store.close()

    with pytest.raises(RuntimeError, match="causal_history_incomplete"):
        DistributedMemoryStore(path, actor_id="receiver")



def test_export_rejects_oversized_peer_actor_identifier(tmp_path):
    store = DistributedMemoryStore(str(tmp_path / "memory.sqlite"), actor_id="local")
    with pytest.raises(ValueError, match="invalid_peer_vector_clock"):
        store.export_since({"x" * 257: 0})
    store.close()


def test_startup_rejects_cyclic_cross_actor_causal_history(tmp_path):
    path = str(tmp_path / "cyclic-memory.sqlite")
    store = DistributedMemoryStore(path, actor_id="receiver")
    actor_a = MemoryEvent(
        "peer-a", 1, "a", "from-a", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    actor_b = MemoryEvent(
        "peer-b", 1, "b", "from-b", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    store._db.execute("BEGIN IMMEDIATE")
    try:
        store._insert_event(actor_a)
        store._insert_event(actor_b)
        store._db.execute("COMMIT")
    except Exception:
        if store._db.in_transaction:
            store._db.execute("ROLLBACK")
        raise
    store.close()

    with pytest.raises(RuntimeError, match="causal_history_incomplete"):
        DistributedMemoryStore(path, actor_id="receiver")


def _merge_memory_event_in_process(database_path, event, ready, start, results):
    store = DistributedMemoryStore(database_path, actor_id="receiver")
    try:
        ready.put(True)
        if not start.wait(15):
            results.put(("timeout", None))
            return
        inserted = store.merge((event,))
        results.put(("ok", inserted))
    except Exception as exc:
        results.put(("error", type(exc).__name__ + ":" + str(exc)))
    finally:
        store.close()


def test_independent_processes_merge_concurrent_causal_events_atomically(tmp_path):
    import multiprocessing

    path = str(tmp_path / "concurrent-memory.sqlite")
    initial = DistributedMemoryStore(path, actor_id="receiver")
    initial.close()
    events = (
        MemoryEvent("peer-a", 1, "shared-key", "from-a", False, (("peer-a", 1),)),
        MemoryEvent("peer-b", 1, "shared-key", "from-b", False, (("peer-b", 1),)),
    )
    context = multiprocessing.get_context("spawn")
    ready, start, results = context.Queue(), context.Event(), context.Queue()
    workers = [
        context.Process(
            target=_merge_memory_event_in_process,
            args=(path, event, ready, start, results),
        )
        for event in events
    ]
    for worker in workers:
        worker.start()
    try:
        assert ready.get(timeout=20) is True
        assert ready.get(timeout=20) is True
        start.set()
        for worker in workers:
            worker.join(timeout=25)
        assert all(not worker.is_alive() for worker in workers), "memory_merge_process_timeout"
        assert [worker.exitcode for worker in workers] == [0, 0]
        outcomes = [results.get(timeout=5) for _ in workers]
        assert all(kind == "ok" and count == 1 for kind, count in outcomes), outcomes
    finally:
        start.set()
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        ready.close()
        results.close()

    reopened = DistributedMemoryStore(path, actor_id="receiver")
    try:
        assert reopened.vector_clock() == {"peer-a": 1, "peer-b": 1}
        conflict = reopened.conflicts("shared-key")
        assert conflict is not None
        assert {conflict.winner.actor_id, *(event.actor_id for event in conflict.concurrent)} == {"peer-a", "peer-b"}
    finally:
        reopened.close()
