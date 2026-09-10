from __future__ import annotations

from .actions import AuthorizationAuthority
from .agent_runtime import AgentRuntime
from .identity import AgentIdentity
from .jarvis_runtime_bridge import JarvisRuntimeBridge
from .operational_fabric import OperationalAgentFabric
from .planning import Planner
from .runtime import NORYXRuntime
from .system_fabric import CanonicalSystemFabric
from .training_governance import EvaluationReport, TrainingGovernance, TrainingStage
from noryx7_runtime.engine import RuntimeEngine


class OperationalNORYXRuntime(NORYXRuntime):
    """NORYX7 runtime with hosted agents and one canonical operational fabric."""

    REQUIRED_AGENT_IDS = frozenset({"noryx7-llm", "noryx7-secondary"})
    MODEL_EXECUTE_CAPABILITY = "model:execute"

    def __init__(self, limits=None, *, state_journal_path=None, model_fabric=None, user_understanding=None):
        if model_fabric is None:
            raise ValueError("model_fabric_required_for_operational_agents")
        super().__init__(limits, state_journal_path=state_journal_path, model_fabric=model_fabric, user_understanding=user_understanding)
        self.system_fabric = CanonicalSystemFabric()
        self.router.system_fabric = self.system_fabric
        self.training_governance = TrainingGovernance()
        self.agent_runtime = AgentRuntime(self.router, self.identity_registry)
        self.agent_fabric = OperationalAgentFabric(self.router, self.verifier, audit=self.audit)
        self._jarvis_bridge: JarvisRuntimeBridge | None = None
        self.hypersynth.kernel.planner = Planner(max_steps=min(self.limits.max_actions_per_task, 2), collaboration_enabled=True)
        self.hypersynth.kernel.supervisor = self.agent_fabric
        for agent_id in sorted(self.REQUIRED_AGENT_IDS):
            agent = self.router.get(agent_id)
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
                raise RuntimeError("operational_agent_identity_invalid")
            self.system_fabric.bind_agent_identity(identity, capabilities=("execute", self.MODEL_EXECUTE_CAPABILITY))
        statuses = self.agent_runtime.start()
        status_ids = {item.agent_id for item in statuses}
        if not self.REQUIRED_AGENT_IDS.issubset(status_ids):
            self.agent_runtime.stop(); raise RuntimeError("primary_secondary_agents_missing")
        if not statuses or not all(item.state == "ONLINE" for item in statuses):
            self.agent_runtime.stop(); raise RuntimeError("agent_runtime_not_online")
        fabric_ids = set(self.agent_fabric.available())
        if not self.REQUIRED_AGENT_IDS.issubset(fabric_ids):
            self.agent_runtime.stop(); raise RuntimeError("operational_fabric_agents_missing")
        self.audit.record("agent_runtime_online", agents=tuple(item.agent_id for item in statuses), states=tuple(item.state for item in statuses), required_agents=tuple(sorted(self.REQUIRED_AGENT_IDS)), operational_fabric=tuple(sorted(fabric_ids)))

    def _record_canonical_execution(self, *, execution_id: str, phase: str, metadata) -> None:
        self.system_fabric.record_execution(execution_id=execution_id, client_id="noryx7-runtime", phase=phase, metadata=metadata)
        self.audit.record(f"canonical_system_execution_{phase}", execution_id=execution_id, phase=phase)

    def run_hypersynth(self, task, interaction_context=None):
        execution_id = getattr(task, "execution_id", None)
        if not isinstance(execution_id, str) or not execution_id:
            return super().run_hypersynth(task, interaction_context=interaction_context)
        self._record_canonical_execution(execution_id=execution_id, phase="runtime_received", metadata={"task_id": getattr(task, "task_id", ""), "task_type": getattr(task, "task_type", "")})
        result = super().run_hypersynth(task, interaction_context=interaction_context)
        if isinstance(result, dict) and result.get("status") == "completed":
            self._record_canonical_execution(execution_id=execution_id, phase="runtime_committed", metadata={"task_id": getattr(task, "task_id", ""), "verified": True, "orchestration_stage": result.get("orchestration_stage", "")})
        elif isinstance(result, dict):
            self._record_canonical_execution(execution_id=execution_id, phase="runtime_rejected", metadata={"task_id": getattr(task, "task_id", ""), "reason": result.get("reason", "runtime_rejected")})
        return result

    def admit_training_candidate(self, report: EvaluationReport) -> TrainingStage:
        """Evaluate a model candidate without changing the active model implicitly."""
        if not isinstance(report, EvaluationReport):
            raise TypeError("evaluation_report_required")
        stage = self.training_governance.admit(report)
        self.system_fabric.record_execution(execution_id=f"training:{report.candidate_id}", client_id="noryx7-training", phase=stage.value, metadata={"candidate_id": report.candidate_id, "baseline_score": report.baseline_score, "candidate_score": report.candidate_score, "safety_score": report.safety_score, "regression_free": report.regression_free})
        self.audit.record("training_candidate_evaluated", candidate_id=report.candidate_id, stage=stage.value)
        return stage

    def configure_jarvis_bridge(self, *, runtime_engine: RuntimeEngine, authorization: AuthorizationAuthority, principal: AgentIdentity, policy) -> JarvisRuntimeBridge:
        bridge = JarvisRuntimeBridge(runtime_engine=runtime_engine, tool_executor=self.tool_executor, verifier=self.verifier, authorization=authorization, principal=principal, policy=policy, system_fabric=self.system_fabric)
        self._jarvis_bridge = bridge
        self.audit.record("jarvis_runtime_bridge_bound", runtime_id=runtime_engine.runtime_id, principal_id=principal.agent_id, system_fabric="canonical")
        return bridge

    @property
    def jarvis_bridge(self) -> JarvisRuntimeBridge | None:
        return self._jarvis_bridge

    def execute_jarvis(self, request, plan):
        if self._jarvis_bridge is None:
            raise RuntimeError("jarvis_bridge_not_configured")
        return self._jarvis_bridge.execute(request, plan)

    def heartbeat_agents(self):
        statuses = self.agent_runtime.heartbeat()
        status_ids = {item.agent_id for item in statuses}
        if not self.REQUIRED_AGENT_IDS.issubset(status_ids) or not all(item.state == "ONLINE" for item in statuses):
            raise RuntimeError("agent_runtime_not_online")
        fabric_online = set(self.agent_fabric.online())
        if not self.REQUIRED_AGENT_IDS.issubset(fabric_online):
            raise RuntimeError("operational_fabric_not_online")
        return statuses

    def shutdown_agents(self):
        self.agent_runtime.stop()
