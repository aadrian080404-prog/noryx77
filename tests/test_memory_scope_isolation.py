import pytest

from core.memory import MemoryItem, MemoryStore


def item(memory_id="shared", content="value", *, principal="", agent="", execution=""):
    return MemoryItem(
        memory_id=memory_id,
        content=content,
        principal_id=principal,
        agent_id=agent,
        execution_id=execution,
    )


def test_same_memory_id_isolated_between_principals():
    store = MemoryStore()
    store.put(item(content="tenant-a", principal="tenant-a"))
    store.put(item(content="tenant-b", principal="tenant-b"))

    assert store.get("shared", principal_id="tenant-a").content == "tenant-a"
    assert store.get("shared", principal_id="tenant-b").content == "tenant-b"
    assert store.get("shared") is None


def test_agent_memory_isolated_from_other_agents_and_principal_memory():
    store = MemoryStore()
    store.put(item(content="tenant-wide", principal="tenant-a"))
    store.put(item(content="agent-one", principal="tenant-a", agent="agent-1"))
    store.put(item(content="agent-two", principal="tenant-a", agent="agent-2"))

    assert store.get("shared", principal_id="tenant-a").content == "tenant-wide"
    assert store.get("shared", principal_id="tenant-a", agent_id="agent-1").content == "agent-one"
    assert store.get("shared", principal_id="tenant-a", agent_id="agent-2").content == "agent-two"
    assert store.get("shared", principal_id="tenant-a", agent_id="agent-3") is None
    assert store.get("shared", principal_id="tenant-a") .content == "tenant-wide"


def test_execution_scoped_memory_requires_exact_execution_even_for_same_principal():
    store = MemoryStore()
    store.put(item(content="run-one", principal="tenant-a", execution="exec-1"))
    store.put(item(content="run-two", principal="tenant-a", execution="exec-2"))

    assert store.get("shared", principal_id="tenant-a", execution_id="exec-1").content == "run-one"
    assert store.get("shared", principal_id="tenant-a", execution_id="exec-2").content == "run-two"
    assert store.get("shared", principal_id="tenant-a") is None
    assert store.get("shared", execution_id="exec-1") is None


def test_legacy_unscoped_api_only_sees_global_records():
    store = MemoryStore()
    store.put(item(content="global"))
    store.put(item(content="tenant", principal="tenant-a"))
    store.put(item(content="execution", execution="exec-1"))

    assert store.get("shared").content == "global"
    assert [x.content for x in store.list()] == ["global"]
    assert store.get("shared", execution_id="exec-1").content == "execution"
    assert [x.content for x in store.list(execution_id="exec-1")] == ["execution"]


def test_list_and_delete_use_exact_namespace():
    store = MemoryStore()
    store.put(item(content="a1", principal="tenant-a", agent="agent-1"))
    store.put(item(content="a2", principal="tenant-a", agent="agent-2"))
    store.put(item(content="b1", principal="tenant-b", agent="agent-1"))

    assert [x.content for x in store.list(principal_id="tenant-a", agent_id="agent-1")] == ["a1"]
    assert store.delete("shared", principal_id="tenant-a", agent_id="agent-1")
    assert store.get("shared", principal_id="tenant-a", agent_id="agent-1") is None
    assert store.get("shared", principal_id="tenant-a", agent_id="agent-2").content == "a2"
    assert store.get("shared", principal_id="tenant-b", agent_id="agent-1").content == "b1"


def test_rejects_agent_scope_without_principal_and_invalid_scope_values():
    store = MemoryStore()
    with pytest.raises(ValueError, match="agent_scoped_memory_requires_principal"):
        store.put(item(agent="agent-1"))
    assert store.get("shared", agent_id="agent-1") is None
    assert store.list(principal_id="") == ()
    assert store.delete("shared", principal_id=" " ) is False


def test_scoped_reads_return_deep_copies():
    store = MemoryStore()
    payload = {"nested": ["before"]}
    store.put(item(content=payload, principal="tenant-a"))
    result = store.get("shared", principal_id="tenant-a")
    result.content["nested"].append("after")
    assert store.get("shared", principal_id="tenant-a").content == {"nested": ["before"]}


def test_capacity_counts_distinct_scoped_records():
    store = MemoryStore(max_items=2)
    store.put(item(content="a", principal="tenant-a"))
    store.put(item(content="b", principal="tenant-b"))
    with pytest.raises(MemoryError, match="memory_capacity_exceeded"):
        store.put(item(content="global"))
