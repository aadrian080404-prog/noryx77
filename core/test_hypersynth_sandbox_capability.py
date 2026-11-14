import pytest

from core.contracts import ActionSpec
from core.hypersynth_runtime import HypersynthRuntime
from core.execution_fabric import ProposedAction


class FakeSandboxAdapter:
    environment = "sandboxed_process"

    def __init__(self):
        self.actions = []

    def execute(self, action):
        self.actions.append(action)
        return {"status": "sandboxed", "argv": tuple(action.parameters["argv"])}


def test_sandbox_capability_is_absent_unless_explicitly_configured():
    runtime = HypersynthRuntime()
    assert "sandboxed_process" not in runtime.tool_executor.capabilities.names()


def test_configured_sandbox_capability_is_high_risk_and_narrow():
    adapter = FakeSandboxAdapter()
    runtime = HypersynthRuntime(sandboxed_process_adapter=adapter)
    assert runtime.tool_executor.capabilities.risk("sandboxed_process") == "high"
    handler = runtime.tool_executor.capabilities.resolve("sandboxed_process")
    result = handler("workspace", {"action_id": "action-1", "argv": ["python", "-V"]})
    assert result == {"status": "sandboxed", "argv": ("python", "-V")}
    assert adapter.actions == [ProposedAction(
        environment="sandboxed_process", action_id="action-1",
        action_type="process", target="workspace",
        parameters={"argv": ["python", "-V"]},
    )]


def test_sandbox_capability_rejects_missing_action_id():
    runtime = HypersynthRuntime(sandboxed_process_adapter=FakeSandboxAdapter())
    handler = runtime.tool_executor.capabilities.resolve("sandboxed_process")
    with pytest.raises(ValueError, match="sandbox_action_id_required"):
        handler("workspace", {"argv": ["python", "-V"]})


def test_sandbox_capability_rejects_invalid_adapter():
    with pytest.raises(TypeError, match="invalid_sandboxed_process_adapter"):
        HypersynthRuntime(sandboxed_process_adapter=object())


def test_tool_executor_does_not_run_high_risk_sandbox_without_authorization():
    adapter = FakeSandboxAdapter()
    runtime = HypersynthRuntime(sandboxed_process_adapter=adapter)
    action = ActionSpec(
        "sandbox-unauthorized", "sandboxed_process", target="workspace",
        parameters={"action_id": "sandbox-unauthorized", "argv": ["python", "-V"]},
        risk_class="high", requires_authorization=True, execution_id="exec-sandbox-1",
    )
    output, check = runtime.tool_executor.execute(action, execution_id="exec-sandbox-1")
    assert output is None
    assert not check.valid
    assert check.reason == "authorization_required"
    assert adapter.actions == []
