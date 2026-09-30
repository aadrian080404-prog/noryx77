from core.execution_fabric import ExecutionFabric, Observation, ProposedAction
from core.execution_trace import ExecutionTrace


class _Adapter:
    environment = "test"

    def observe(self):
        return Observation("test", "obs-1", {"ok": True})

    def execute(self, action):
        return {"action": action.action_id}


def test_execution_fabric_denies_before_adapter_execution():
    called = []
    adapter = _Adapter()
    adapter.execute = lambda action: called.append(action) or {"ok": True}
    fabric = ExecutionFabric(authorize=lambda action: False)
    fabric.register(adapter)
    try:
        fabric.execute(ProposedAction("test", "a-1", "click", "target", {}))
    except PermissionError as exc:
        assert str(exc) == "execution_not_authorized"
    else:
        raise AssertionError("unauthorized execution must fail closed")
    assert called == []


def test_execution_fabric_observation_is_bound_to_environment():
    fabric = ExecutionFabric(authorize=lambda action: True)
    fabric.register(_Adapter())
    assert fabric.observe("test").environment == "test"


def test_execution_trace_is_chain_verifiable():
    trace = ExecutionTrace("exec-1")
    trace.append("plan", {"step": 1})
    trace.append("action", {"step": 1, "result": "ok"})
    assert trace.verify() is True
    assert len(trace.events()) == 2
