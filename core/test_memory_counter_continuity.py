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


def _write_local_memory_in_process(database_path, key, ready, start, results):
    store = DistributedMemoryStore(database_path, actor_id="shared-local-actor")
    try:
        ready.put(True)
        if not start.wait(15):
            results.put(("timeout", None))
            return
        event = store.write(key, "value:" + key)
        results.put(("ok", event.counter))
    except Exception as exc:
        results.put(("error", type(exc).__name__ + ":" + str(exc)))
    finally:
        store.close()


def test_independent_processes_serialize_local_actor_counters(tmp_path):
    import multiprocessing

    path = str(tmp_path / "same-actor-concurrent-memory.sqlite")
    initial = DistributedMemoryStore(path, actor_id="shared-local-actor")
    initial.close()
    context = multiprocessing.get_context("spawn")
    ready, start, results = context.Queue(), context.Event(), context.Queue()
    keys = ("left", "right", "center", "edge")
    workers = [
        context.Process(
            target=_write_local_memory_in_process,
            args=(path, key, ready, start, results),
        )
        for key in keys
    ]
    for worker in workers:
        worker.start()
    try:
        for _ in workers:
            assert ready.get(timeout=20) is True
        start.set()
        for worker in workers:
            worker.join(timeout=25)
        assert all(not worker.is_alive() for worker in workers), "memory_local_writer_timeout"
        assert [worker.exitcode for worker in workers] == [0] * len(workers)
        outcomes = [results.get(timeout=5) for _ in workers]
        assert all(kind == "ok" for kind, _counter in outcomes), outcomes
        assert sorted(counter for _kind, counter in outcomes) == [1, 2, 3, 4]
    finally:
        start.set()
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        ready.close()
        results.close()

    reopened = DistributedMemoryStore(path, actor_id="shared-local-actor")
    try:
        assert reopened.vector_clock() == {"shared-local-actor": 4}
        assert len(reopened.export_since({})) == 4
    finally:
        reopened.close()


def _crash_during_uncommitted_memory_append(database_path):
    import os

    store = DistributedMemoryStore(database_path, actor_id="crash-actor")
    store._db.execute("BEGIN IMMEDIATE")
    event = MemoryEvent(
        "crash-actor", 1, "uncommitted", "must-not-survive", False,
        (("crash-actor", 1),),
    )
    store._insert_event(event)
    # Simulate abrupt process death without rollback or close.
    os._exit(74)


def test_memory_recovers_uncommitted_append_after_process_death(tmp_path):
    import multiprocessing

    path = str(tmp_path / "memory-process-crash.sqlite")
    initial = DistributedMemoryStore(path, actor_id="crash-actor")
    initial.close()

    context = multiprocessing.get_context("spawn")
    worker = context.Process(
        target=_crash_during_uncommitted_memory_append,
        args=(path,),
    )
    worker.start()
    worker.join(timeout=20)
    try:
        assert not worker.is_alive(), "memory_crash_probe_timeout"
        assert worker.exitcode == 74
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)

    recovered = DistributedMemoryStore(path, actor_id="crash-actor")
    try:
        assert recovered.vector_clock() == {}
        assert recovered.read("uncommitted") is None
        committed = recovered.write("after-recovery", "committed")
        assert committed.counter == 1
        assert recovered.vector_clock() == {"crash-actor": 1}
    finally:
        recovered.close()


def test_export_since_limit_preserves_cross_actor_causal_dependencies(tmp_path):
    source = DistributedMemoryStore(str(tmp_path / "source-causal-pages.sqlite"), actor_id="source")
    dependency = MemoryEvent("peer-b", 1, "source", "base", False, (("peer-b", 1),))
    dependent = MemoryEvent(
        "peer-a", 1, "derived", "computed", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    try:
        assert source.merge((dependent, dependency)) == 2
        first_page = source.export_since({}, limit=1)
        assert first_page == (dependency,)

        target = DistributedMemoryStore(str(tmp_path / "target-causal-pages.sqlite"), actor_id="target")
        try:
            assert target.merge(first_page) == 1
            next_clock = target.vector_clock()
            second_page = source.export_since(next_clock, limit=1)
            assert second_page == (dependent,)
            assert target.merge(second_page) == 1
            assert target.read("derived") == dependent
        finally:
            target.close()
    finally:
        source.close()


def test_paginated_causal_replication_is_idempotent_across_retries(tmp_path):
    source = DistributedMemoryStore(str(tmp_path / "source-retry-pages.sqlite"), actor_id="source")
    target = DistributedMemoryStore(str(tmp_path / "target-retry-pages.sqlite"), actor_id="target")
    dependency = MemoryEvent("peer-b", 1, "b", "base", False, (("peer-b", 1),))
    dependent = MemoryEvent(
        "peer-a", 1, "a", "derived", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    transitive = MemoryEvent(
        "peer-c", 1, "c", "transitive", False,
        (("peer-a", 1), ("peer-b", 1), ("peer-c", 1)),
    )
    try:
        assert source.merge((transitive, dependent, dependency)) == 3
        delivered = []
        for expected in (dependency, dependent, transitive):
            page = source.export_since(target.vector_clock(), limit=1)
            assert page == (expected,)
            assert target.merge(page) == 1
            delivered.extend(page)
            # A retry of the last successfully delivered page must be harmless.
            assert target.merge(page) == 0
        assert source.export_since(target.vector_clock(), limit=1) == ()
        assert target.vector_clock() == {
            "peer-a": 1, "peer-b": 1, "peer-c": 1,
        }
        assert target.read("c") == transitive
    finally:
        source.close()
        target.close()


def test_causal_replication_resumes_after_receiver_restart_between_pages(tmp_path):
    source = DistributedMemoryStore(str(tmp_path / "restart-source.sqlite"), actor_id="source")
    target_path = str(tmp_path / "restart-target.sqlite")
    target = DistributedMemoryStore(target_path, actor_id="target")
    dependency = MemoryEvent("peer-b", 1, "base", "ready", False, (("peer-b", 1),))
    dependent = MemoryEvent(
        "peer-a", 1, "derived", "complete", False,
        (("peer-a", 1), ("peer-b", 1)),
    )
    try:
        assert source.merge((dependent, dependency)) == 2
        first_page = source.export_since(target.vector_clock(), limit=1)
        assert first_page == (dependency,)
        assert target.merge(first_page) == 1
        target.close()

        target = DistributedMemoryStore(target_path, actor_id="target")
        assert target.vector_clock() == {"peer-b": 1}
        second_page = source.export_since(target.vector_clock(), limit=1)
        assert second_page == (dependent,)
        assert target.merge(second_page) == 1
        assert target.read("derived") == dependent
        assert source.export_since(target.vector_clock(), limit=1) == ()
    finally:
        source.close()
        target.close()


def test_merge_rejects_equivocating_duplicate_actor_counter_atomically(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "equivocation.sqlite"), actor_id="receiver")
    first = MemoryEvent("peer", 1, "key-a", "value-a", False, (("peer", 1),))
    conflicting = MemoryEvent("peer", 1, "key-b", "value-b", False, (("peer", 1),))

    with pytest.raises(ValueError, match="memory_batch_equivocation"):
        target.merge((first, conflicting))

    assert target.vector_clock() == {}
    assert target.read("key-a") is None
    assert target.read("key-b") is None
    target.close()
