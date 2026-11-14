"""ExecutionFabric adapter that routes process actions through Bubblewrap."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .execution_fabric import Observation, ProposedAction
from .os_sandbox import BubblewrapSandboxRunner, SandboxLimits, SandboxResult


class SandboxedProcessAdapter:
    """Narrow process adapter; all execution is delegated to Bubblewrap.

    This adapter deliberately exposes no shell, network, host filesystem,
    environment or arbitrary working-directory controls through action data.
    The caller supplies one pre-created workspace path and an argv vector.
    """

    environment = "sandboxed_process"

    def __init__(
        self,
        runner: BubblewrapSandboxRunner,
        *,
        workspace: str | Path,
        limits: SandboxLimits = SandboxLimits(),
    ) -> None:
        if not isinstance(runner, BubblewrapSandboxRunner):
            raise TypeError("bubblewrap_runner_required")
        if not isinstance(limits, SandboxLimits):
            raise TypeError("sandbox_limits_required")
        if not isinstance(workspace, (str, Path)) or not str(workspace):
            raise ValueError("sandbox_workspace_required")
        self._runner = runner
        self._workspace = Path(workspace)
        self._limits = limits

    def observe(self) -> Observation:
        workspace = self._runner._workspace_path(self._workspace)
        return Observation(
            environment=self.environment,
            observation_id="workspace:" + workspace,
            payload={"workspace": workspace, "network": "disabled"},
        )

    def execute(self, action: ProposedAction) -> SandboxResult:
        if not isinstance(action, ProposedAction):
            raise TypeError("proposed_action_required")
        if action.environment != self.environment:
            raise PermissionError("sandbox_environment_mismatch")
        if action.action_type != "process" or action.target != "workspace":
            raise PermissionError("sandbox_action_not_supported")
        if not isinstance(action.parameters, Mapping):
            raise TypeError("sandbox_action_parameters_required")
        if set(action.parameters) != {"argv"}:
            raise ValueError("sandbox_action_parameters_invalid")
        argv = action.parameters["argv"]
        return self._runner.run(argv, workspace=self._workspace, limits=self._limits)
