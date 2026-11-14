import pytest

from core.execution_fabric import ExecutionFabric, ProposedAction
from core.os_sandbox import BubblewrapSandboxRunner, SandboxLimits, SandboxResult
from core.sandboxed_execution import SandboxedProcessAdapter


class FakeRunner:
    def __init__(self):
        self.calls = []

    @staticmethod
    def _workspace_path(workspace):
        return str(workspace)

    def run(self, argv, *, workspace, limits):
        self.calls.append((tuple(argv), str(workspace), limits))
        return SandboxResult(0, b"ok", b"", False, False)


def test_execution_fabric_routes_authorized_process_to_sandbox(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    runner = FakeRunner()
    adapter = SandboxedProcessAdapter(
        runner, workspace=workspace, limits=SandboxLimits()
    )
    fabric = ExecutionFabric(authorize=lambda action: True)
    fabric.register(adapter)
    action = ProposedAction(
        "sandboxed_process", "run-1", "process", "workspace",
        {"argv": ["/usr/bin/python3", "-V"]},
    )
    result = fabric.execute(action)
    assert result.stdout == b"ok"
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == ("/usr/bin/python3", "-V")


def test_denied_action_never_reaches_sandbox(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    runner = FakeRunner()
    fabric = ExecutionFabric(authorize=lambda action: False)
    fabric.register(SandboxedProcessAdapter(runner, workspace=workspace))
    action = ProposedAction(
        "sandboxed_process", "run-2", "process", "workspace",
        {"argv": ["/usr/bin/python3", "-V"]},
    )
    with pytest.raises(PermissionError, match="not_authorized"):
        fabric.execute(action)
    assert runner.calls == []


@pytest.mark.parametrize("action", [
    ProposedAction("sandboxed_process", "x", "shell", "workspace", {"argv": ["sh"]}),
    ProposedAction("sandboxed_process", "x", "process", "host", {"argv": ["/bin/true"]}),
    ProposedAction("sandboxed_process", "x", "process", "workspace",
                   {"argv": ["/bin/true"], "env": {"TOKEN": "secret"}}),
])
def test_adapter_rejects_shell_host_target_and_extra_capabilities(tmp_path, action):
    workspace = tmp_path / "work"
    workspace.mkdir()
    fabric = ExecutionFabric(authorize=lambda _: True)
    fabric.register(SandboxedProcessAdapter(FakeRunner(), workspace=workspace))
    with pytest.raises((PermissionError, ValueError)):
        fabric.execute(action)


def test_adapter_requires_real_bubblewrap_runner(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    with pytest.raises(TypeError, match="sandbox_runner_contract"):
        SandboxedProcessAdapter(object(), workspace=workspace)
