import pytest

from core.memory import MemoryItem, MemoryStore
from core.sqlite_memory import SQLiteEncryptedMemoryStore
from core.tiered_memory import TieredMemoryRouter


KEY = b"t" * 32


def local_store(path):
    return SQLiteEncryptedMemoryStore(
        str(path), encryption_key=KEY, key_id="tiered-memory-v1", max_items=100
    )


def test_tiered_router_routes_memory_to_explicit_backends(tmp_path):
    working = MemoryStore()
    local = local_store(tmp_path / "local.sqlite")
    edge = MemoryStore()
    cloud = MemoryStore()
    router = TieredMemoryRouter(
        working_store=working, local_store=local, edge_store=edge, cloud_store=cloud
    )
    items = [
        MemoryItem("w", "volatile", kind="working", execution_id="e1"),
        MemoryItem("l", "encrypted", kind="local", execution_id="e1"),
        MemoryItem("lt", "long", kind="long_term", execution_id="e1"),
        MemoryItem("s", "suspended", kind="suspended", execution_id="e1"),
        MemoryItem("ed", "edge", kind="edge", execution_id="e1"),
        MemoryItem("c", "cloud", kind="cloud", execution_id="e1"),
    ]
    for item in items:
        router.put(item)

    assert working.get("w") == items[0]
    assert local.get("l") == items[1]
    assert local.get("lt") == items[2]
    assert local.get("s") == items[3]
    assert edge.get("ed") == items[4]
    assert cloud.get("c") == items[5]
    assert router.list(execution_id="e1") == tuple(sorted(items, key=lambda x: x.memory_id))
    assert router.get("l", execution_id="other") is None
    router.close()


def test_missing_edge_or_cloud_tier_fails_without_fallback(tmp_path):
    router = TieredMemoryRouter(local_store=local_store(tmp_path / "local.sqlite"))
    with pytest.raises(RuntimeError, match="memory_tier_unavailable:edge"):
        router.put(MemoryItem("edge", "must not fall back", kind="edge"))
    with pytest.raises(RuntimeError, match="memory_tier_unavailable:cloud"):
        router.put(MemoryItem("cloud", "must not fall back", kind="cloud"))
    router.close()


def test_router_requires_durable_local_backend_by_default():
    with pytest.raises(ValueError, match="durable_local_memory_store_required"):
        TieredMemoryRouter()


def test_router_detects_duplicate_ids_across_tiers(tmp_path):
    local = local_store(tmp_path / "local.sqlite")
    working = MemoryStore()
    local.put(MemoryItem("duplicate", "local", kind="local"))
    working.put(MemoryItem("duplicate", "working", kind="working"))
    router = TieredMemoryRouter(working_store=working, local_store=local)
    with pytest.raises(RuntimeError, match="duplicate_memory_id"):
        router.get("duplicate")
    with pytest.raises(RuntimeError, match="duplicate_memory_id"):
        router.list()
    router.close()


def test_router_closes_durable_store_and_rejects_future_access(tmp_path):
    local = local_store(tmp_path / "local.sqlite")
    router = TieredMemoryRouter(local_store=local)
    assert router.durable
    router.close()
    assert not router.durable
    with pytest.raises(RuntimeError, match="closed"):
        router.list()
