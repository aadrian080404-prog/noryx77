import pytest

from core.distributed_memory import DistributedMemoryStore, MemoryEvent


def open_store(tmp_path, actor):
    return DistributedMemoryStore(str(tmp_path / f"{actor}.sqlite"), actor_id=actor)


def test_offline_replication_is_idempotent_and_converges(tmp_path):
    a = open_store(tmp_path, "node-a")
    b = open_store(tmp_path, "node-b")
    a.write("profile", "one")
    b.write("other", "two")
    batch_a = a.export_since({})
    batch_b = b.export_since({})
    assert b.merge(batch_a) == 1
    assert a.merge(batch_b) == 1
    assert b.merge(batch_a) == 0
    assert a.read("profile").value == "one"
    assert b.read("other").value == "two"
    assert a.vector_clock() == b.vector_clock()
    a.close()
    b.close()


def test_causal_update_dominates_old_value(tmp_path):
    a = open_store(tmp_path, "node-a")
    b = open_store(tmp_path, "node-b")
    first = a.write("k", "old")
    b.merge((first,))
    newer = b.write("k", "new")
    a.merge((newer,))
    assert a.read("k").value == "new"
    assert a.conflicts("k") is None
    a.close()
    b.close()


def test_concurrent_updates_are_retained_and_conflict_is_deterministic(tmp_path):
    a = open_store(tmp_path, "node-a")
    b = open_store(tmp_path, "node-b")
    a.write("k", "from-a")
    b.write("k", "from-b")
    a.merge(b.export_since({}))
    b.merge(a.export_since({}))
    conflict_a = a.conflicts("k")
    conflict_b = b.conflicts("k")
    assert conflict_a is not None and conflict_b is not None
    assert conflict_a.winner == conflict_b.winner
    assert len(conflict_a.concurrent) == 1
    assert a.read("k") == b.read("k")
    a.close()
    b.close()


def test_tombstone_replicates_and_hides_old_value(tmp_path):
    a = open_store(tmp_path, "node-a")
    b = open_store(tmp_path, "node-b")
    created = a.write("k", "secret")
    b.merge((created,))
    deleted = b.delete("k")
    a.merge((deleted,))
    assert a.read("k") is None
    assert b.read("k") is None
    a.close()
    b.close()


def test_rejects_actor_counter_equivocation_and_bad_clock(tmp_path):
    a = open_store(tmp_path, "node-a")
    event = a.write("k", "value")
    forged = MemoryEvent(event.actor_id, event.counter, "k", "different", False, event.clock)
    b = open_store(tmp_path, "node-b")
    b.merge((event,))
    with pytest.raises(ValueError, match="equivocation"):
        b.merge((forged,))
    with pytest.raises(ValueError, match="clock_mismatch"):
        MemoryEvent("x", 1, "k", "v", False, (("x", 2),)).validate()
    a.close()
    b.close()


def test_database_is_bound_to_stable_node_identity(tmp_path):
    a = open_store(tmp_path, "node-a")
    a.write("k", "v")
    a.close()
    with pytest.raises(ValueError, match="actor_mismatch"):
        DistributedMemoryStore(str(tmp_path / "node-a.sqlite"), actor_id="node-b")


def test_restart_preserves_event_log_and_clock(tmp_path):
    path = str(tmp_path / "node.sqlite")
    a = DistributedMemoryStore(path, actor_id="node-a")
    a.write("k", "persisted")
    clock = a.vector_clock()
    a.close()
    reopened = DistributedMemoryStore(path, actor_id="node-a")
    assert reopened.vector_clock() == clock
    assert reopened.read("k").value == "persisted"
    reopened.close()
