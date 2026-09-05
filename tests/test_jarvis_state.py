from jarvis.core.contracts import ActionResult
from jarvis.core.state import JarvisState, JarvisStateStore


def test_jarvis_state_commits_only_verified_complete_results():
    store = JarvisStateStore()
    state = JarvisState(
        execution_id="exec-1",
        request_id="req-1",
        principal_id="principal-1",
        request_digest=store.digest_request("hello"),
        completed_steps=["step-1"],
        results=[{"step_id": "step-1", "success": True, "output": "ok"}],
    )
    commit = store.commit(state, verified_results=True, execution_id="exec-1", request_id="req-1")
    assert commit.state.status == "committed"
    assert store.get("exec-1").state.request_digest == state.request_digest


def test_jarvis_state_rejects_unverified_results():
    store = JarvisStateStore()
    state = JarvisState("exec-1", "req-1", "principal-1", store.digest_request("hello"))
    try:
        store.commit(state, verified_results=False, execution_id="exec-1", request_id="req-1")
    except PermissionError as exc:
        assert str(exc) == "verified_results_required"
    else:
        raise AssertionError("unverified state was committed")


def test_jarvis_runtime_result_shape_is_available_to_state_layer():
    result = ActionResult("step-1", True, output="ok")
    assert result.success is True
    assert result.step_id == "step-1"
