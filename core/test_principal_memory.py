import pytest

from core.memory_hierarchy import MemoryLevel, MemoryRecord
from core.principal_memory import PrincipalMemoryHierarchy


def test_principal_memory_isolates_identical_keys():
    memory = PrincipalMemoryHierarchy(records_per_principal=4)
    memory.put("tenant-a", MemoryRecord("profile", "A-private", MemoryLevel.L1))
    memory.put("tenant-b", MemoryRecord("profile", "B-private", MemoryLevel.L1))

    assert memory.get("tenant-a", "profile").value == "A-private"
    assert memory.get("tenant-b", "profile").value == "B-private"
    assert memory.get("tenant-c", "profile") is None
    assert [item.value for item in memory.snapshot("tenant-a")] == ["A-private"]


def test_principal_memory_enforces_per_principal_capacity():
    memory = PrincipalMemoryHierarchy(records_per_principal=1)
    memory.put("tenant-a", MemoryRecord("one", "1", MemoryLevel.L0))
    with pytest.raises(MemoryError, match="memory_capacity_reached"):
        memory.put("tenant-a", MemoryRecord("two", "2", MemoryLevel.L0))
    memory.put("tenant-b", MemoryRecord("two", "2", MemoryLevel.L0))
    assert memory.get("tenant-b", "two") is not None


def test_principal_memory_bounds_principal_count_and_validates_identity():
    memory = PrincipalMemoryHierarchy(max_principals=1)
    memory.put("tenant-a", MemoryRecord("k", "v", MemoryLevel.L0))
    with pytest.raises(MemoryError, match="principal_memory_capacity_reached"):
        memory.put("tenant-b", MemoryRecord("k", "v", MemoryLevel.L0))
    with pytest.raises(ValueError, match="invalid_memory_principal"):
        memory.get("", "k")


def test_delete_principal_removes_all_scoped_records():
    memory = PrincipalMemoryHierarchy()
    memory.put("tenant-a", MemoryRecord("a", "1", MemoryLevel.L0))
    memory.put("tenant-a", MemoryRecord("b", "2", MemoryLevel.L1))
    assert memory.delete_principal("tenant-a") is True
    assert memory.snapshot("tenant-a") == ()
    assert memory.principal_count() == 0
    assert memory.delete_principal("tenant-a") is False
