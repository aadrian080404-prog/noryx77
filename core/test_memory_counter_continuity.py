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
