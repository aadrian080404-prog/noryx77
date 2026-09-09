from __future__ import annotations

from uuid import uuid4

from ecosystem.operational_bridge import OperationalEcosystemBridge

from .agent_runtime import AgentRuntime
from .operational_fabric import OperationalAgentFabric
from .planning import Planner
from .runtime import NORYXRuntime


class OperationalNORYXRuntime(NORYXRuntime):
    """NORYX7 runtime with hosted agents and one canonical operational fabric."""

    REQUIRED_AGENT_IDS = frozenset({"noryx7-llm", "noryx7-secondary"})

    def __init__(self, limits=None, *, state_journal_path=None, model_fabric=None):
        if model_fabric is None:
            raise ValueError("model_fabric_required_for_operational_agents")
        super().__init__(limits, state_journal_path=state_journal_path, model_fabric=model_fabric)
        self.agent_runtime = AgentRuntime(self.router, self.identity_registry)
        self.agent_fabric = OperationalAgentFabric(self.router, self.verifier, audit=self.audit)
        self.ecosystem_bridge = OperationalEcosystemBridge(
            runtime_id=getattr(model_fabric, "runtime_id", None) or uuid4().hex,
            identity_registry=self.identity_registry,
            memory=self.memory,
        )
        self.hypersynth.kernel.planner = Planner(
            max_steps=min(self.limits.max_actions_per_task, 2),
            collaboration_enabled=True,
        )
        # HYPERSYNTH allocation/execution now traverses the same operational fabric
        # (supervisor -> trusted router -> live agent) rather than a parallel selector.
        self.hypersynth.kernel.supervisor = self.agent_fabric
        statuses = self.agent_runtime.start()
        status_ids = {item.agent_id for item in statuses}
        if not self.REQUIRED_AGENT_IDS.issubset(status_ids):
            self.agent_runtime.stop()
            raise RuntimeError("primary_secondary_agents_missing")
        if not statuses or not all(item.state == "ONLINE" for item in statuses):
            self.agent_runtime.stop()
            raise RuntimeError("agent_runtime_not_online")
        fabric_ids = set(self.agent_fabric.available())
        if not self.REQUIRED_AGENT_IDS.issubset(fabric_ids):
            self.agent_runtime.stop()
            raise RuntimeError("operational_fabric_agents_missing")
        for agent_id in sorted(self.REQUIRED_AGENT_IDS):
            agent = self.router.get(agent_id)
            role = getattr(agent, "role", None) or ("primary" if agent_id == "noryx7-llm" else "secondary")
            self.ecosystem_bridge.bind_agent(
                agent_id=agent_id,
                role=role,
                capabilities=("agent_execution",),
            )
        self.audit.record(
            "agent_runtime_online",
            agents=tuple(item.agent_id for item in statuses),
            states=tuple(item.state for item in statuses),
            required_agents=tuple(sorted(self.REQUIRED_AGENT_IDS)),
            operational_fabric=tuple(sorted(fabric_ids)),
            ecosystem_identity_bindings=tuple(sorted(self.REQUIRED_AGENT_IDS)),
        )

    def heartbeat_agents(self):
        statuses = self.agent_runtime.heartbeat()
        status_ids = {item.agent_id for item in statuses}
        if not self.REQUIRED_AGENT_IDS.issubset(status_ids) or not all(item.state == "ONLINE" for item in statuses):
            raise RuntimeError("agent_runtime_not_online")
        fabric_online = set(self.agent_fabric.online())
        if not self.REQUIRED_AGENT_IDS.issubset(fabric_online):
            raise RuntimeError("operational_fabric_not_online")
        return statuses

    def run_hypersynth(self, task, interaction_context=None):
        result = super().run_hypersynth(task, interaction_context=interaction_context)
        if isinstance(result, dict) and result.get("status") == "completed":
            results = result.get("results")
            if isinstance(results, tuple) and results:
                final = results[-1]
                output = getattr(final, "output", None)
                agent_id = getattr(final, "agent_id", None)
                if isinstance(output, str) and isinstance(agent_id, str):
                    try:
                        self.ecosystem_bridge.record_result(
                            task_id=str(result.get("task_id") or getattr(task, "task_id", "")),
                            execution_id=str(result.get("execution_id") or getattr(task, "execution_id", "")),
                            agent_id=agent_id,
                            output=output,
                        )
                        self.audit.record(
                            "global_memory_indexed",
                            task_id=result.get("task_id"),
                            execution_id=result.get("execution_id"),
                            agent_id=agent_id,
                        )
                    except Exception:
                        # Global indexing is an observability/index layer and must never
                        # turn an already verified core execution into a false success.
                        self.audit.record(
                            "global_memory_index_rejected",
                            task_id=result.get("task_id"),
                            execution_id=result.get("execution_id"),
                            agent_id=agent_id,
                        )
        return result

    def ecosystem_status(self) -> dict[str, object]:
        statuses = self.heartbeat_agents()
        snapshot = self.ecosystem_bridge.snapshot(
            online_agents=tuple(item.agent_id for item in statuses)
        )
        return {
            "runtime_id": snapshot.runtime_id,
            "online_agents": snapshot.online_agents,
            "memory_records": snapshot.memory_records,
            "identity_bindings": snapshot.identity_bindings,
        }

    def shutdown_agents(self):
        self.agent_runtime.stop()
