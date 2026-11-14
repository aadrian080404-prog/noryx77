import pytest

from core.distributed_memory import DistributedMemoryStore, MemoryEvent


def test_merge_requires_cross_actor_dependencies_and_accepts_complete_batch(tmp_path):
    source_a = DistributedMemoryStore(str(tmp_path / "a.sqlite"), actor_id="actor-a")
    source_b = DistributedMemoryStore(str(tmp_path / "b.sqlite"), actor_id="actor-b")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")

    event_a = source_a.write("root", "source")
    assert source_b.merge((event_a,)) == 1
    event_b = source_b.write("derived", "depends-on-root")

    with pytest.raises(ValueError, match="causal_dependency_missing"):
        target.merge((event_b,))
    assert target.vector_clock() == {}

    assert target.merge((event_b, event_a)) == 2
    assert target.vector_clock() == {"actor-a": 1, "actor-b": 1}
    assert target.read("derived") == event_b

    source_a.close()
    source_b.close()
    target.close()


def test_merge_rejects_cyclic_vector_clock_dependencies(tmp_path):
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")
    event_a = MemoryEvent(
        "actor-a", 1, "a", "one", False,
        (("actor-a", 1), ("actor-b", 1)),
    )
    event_b = MemoryEvent(
        "actor-b", 1, "b", "two", False,
        (("actor-a", 1), ("actor-b", 1)),
    )
    with pytest.raises(ValueError, match="causal_dependency_not_prior"):
        target.merge((event_a, event_b))
    assert target.vector_clock() == {}
    target.close()


def test_merge_rejects_transitively_incomplete_history(tmp_path):
    source_a = DistributedMemoryStore(str(tmp_path / "a.sqlite"), actor_id="actor-a")
    source_b = DistributedMemoryStore(str(tmp_path / "b.sqlite"), actor_id="actor-b")
    source_c = DistributedMemoryStore(str(tmp_path / "c.sqlite"), actor_id="actor-c")
    target = DistributedMemoryStore(str(tmp_path / "target.sqlite"), actor_id="receiver")

    event_a = source_a.write("a", "one")
    source_b.merge((event_a,))
    event_b = source_b.write("b", "two")
    source_c.merge((event_a, event_b))
    event_c = source_c.write("c", "three")

    with pytest.raises(ValueError, match="causal_dependency_missing"):
        target.merge((event_b, event_c))
    assert target.vector_clock() == {}

    source_a.close()
    source_b.close()
    source_c.close()
    target.close()
