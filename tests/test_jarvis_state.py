import pytest

from jarvis.core.contracts import Request
from jarvis.core.state import JarvisStateStore


def test_jarvis_state_store_binds_principal_and_isolates_snapshots():
    store = JarvisStateStore()
    request = Request("do work", "principal-a")
    state = store.create(request)
    state.status = "completed"
    state.results.append({"ok": True})
    snapshot = store.commit(state)

    assert snapshot.request_id == request.request_id
    assert store.get(request.request_id, principal_id="principal-a") is not None
    assert store.get(request.request_id, principal_id="principal-b") is None

    state.results[0]["ok"] = False
    stored = store.get(request.request_id, principal_id="principal-a")
    assert stored is not None
    assert stored.state.results == [{"ok": True}]


def test_jarvis_state_store_rejects_invalid_status():
    store = JarvisStateStore()
    state = store.create(Request("do work", "principal-a"))
    state.status = "unknown"
    with pytest.raises(ValueError, match="invalid_state_status"):
        store.commit(state)
