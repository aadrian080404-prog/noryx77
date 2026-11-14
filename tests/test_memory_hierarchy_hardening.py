from concurrent.futures import ThreadPoolExecutor

import pytest

from core.memory_hierarchy import MemoryHierarchy, MemoryLevel, MemoryRecord


def test_capacity_and_update_are_atomic():
    store = MemoryHierarchy(max_records=1)
    store.put(MemoryRecord("a", "one", MemoryLevel.L0))
    store.put(MemoryRecord("a", "updated", MemoryLevel.L1))
    assert len(store) == 1
    assert store.get("a").value == "updated"
    with pytest.raises(MemoryError, match="memory_capacity_reached"):
        store.put(MemoryRecord("b", "two", MemoryLevel.L0))


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5, 1_000_001])
def test_invalid_capacity_rejected(capacity):
    with pytest.raises(ValueError, match="invalid_memory_capacity"):
        MemoryHierarchy(capacity)


@pytest.mark.parametrize(
    "record",
    [
        MemoryRecord("", "v", MemoryLevel.L0),
        MemoryRecord("   ", "v", MemoryLevel.L0),
        MemoryRecord("a", 1, MemoryLevel.L0),
        MemoryRecord("a", "v", 0),
        MemoryRecord("a", "v", "L0"),
    ],
)
def test_invalid_records_rejected(record):
    with pytest.raises((TypeError, ValueError)):
        MemoryHierarchy().put(record)


def test_key_and_value_size_limits():
    store = MemoryHierarchy()
    with pytest.raises(ValueError, match="invalid_memory_key"):
        store.put(MemoryRecord("x" * 1025, "v", MemoryLevel.L0))
    with pytest.raises(ValueError, match="invalid_memory_value"):
        store.put(MemoryRecord("x", "v" * 1_000_001, MemoryLevel.L0))


def test_promotion_and_delete():
    store = MemoryHierarchy()
    store.put(MemoryRecord("k", "v", MemoryLevel.L0))
    promoted = store.promote("k", MemoryLevel.L5)
    assert promoted.level is MemoryLevel.L5
    assert store.delete("k") is True
    assert store.delete("k") is False
    with pytest.raises(KeyError):
        store.promote("missing", MemoryLevel.L1)


def test_invalid_lookup_is_safe():
    store = MemoryHierarchy()
    assert store.get(None) is None
    assert store.get([]) is None


def test_concurrent_writes_respect_capacity():
    store = MemoryHierarchy(max_records=20)

    def write(index):
        try:
            store.put(MemoryRecord(f"k{index}", "v", MemoryLevel.L0))
            return True
        except MemoryError:
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(write, range(100)))
    assert sum(outcomes) == 20
    assert len(store) == 20
    assert len(store.snapshot()) == 20
