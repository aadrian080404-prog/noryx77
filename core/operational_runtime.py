from __future__ import annotations

from .agent_runtime import AgentRuntime
from .planning import Planner
from .runtime import NORYXRuntime


class OperationalNORYXRuntime(NORYXRuntime):
    """NORYX7 runtime with the hosted agent lifecycle and collaboration path enabled."""

    def __init__(self, limits=None, *, state_journal_path=None, model_fabric=None):
        if model_fabric is None:
            raise ValueError("model_fabric_required_for_operational_agents")
        super().__init__(
            limits,
            state_journal_path=state_journal_path,
            model_fabric=model_fabric,
        )
        self.agent_runtime = AgentRuntime(self.router, self.identity_registry)
        # Keep frontier capabilities explicit while routing ordinary model tasks
        # through Primary -> Secondary -> Primary collaboration.
        self.hypersynth.kernel.planner = Planner(
            max_steps=min(self.limits.max_actions_per_task, 2),
            collaboration_enabled=True,
        )
        statuses = self.agent_runtime.start()
        if not statuses or not all(item.state == "ONLINE" for item in statuses):
            raise RuntimeError("agent_runtime_not_online")
        self.audit.record(
            "agent_runtime_online",
            agents=tuple(item.agent_id for item in statuses),
            states=tuple(item.state for item in statuses),
        )

    def heartbeat_agents(self):
        return self.agent_runtime.heartbeat()

    def shutdown_agents(self):
        self.agent_runtime.stop()
