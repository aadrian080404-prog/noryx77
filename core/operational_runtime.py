from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from .actions import AuthorizationAuthority
from .agent_runtime import AgentRuntime
from .agent_continuity import AgentContinuityScheduler
from .contracts import TaskSpec
from .identity import AgentIdentity
from .jarvis_runtime_bridge import JarvisRuntimeBridge
from .operational_fabric import OperationalAgentFabric
from .planning import Planner
from .runtime import NORYXRuntime
from .scientific_fabric import ScientificFabric, PDEProblem
from .scientific_knowledge import ResearchExperiment, ScientificKnowledgeFabric
from .scientific_sources import ArxivSourceProvider, CrossrefSourceProvider, PubMedSourceProvider
from .system_fabric import CanonicalSystemFabric
from .training_governance import EvaluationReport, TrainingGovernance, TrainingStage
from noryx7_runtime.engine import RuntimeEngine


class OperationalNORYXRuntime(NORYXRuntime):
    """NORYX7 runtime with hosted agents and one canonical operational fabric."""

    REQUIRED_AGENT_IDS = frozenset({"noryx7-llm", "noryx7-secondary"})
    MODEL_EXECUTE_CAPABILITY = "model:execute"
    SCIENTIFIC_EXECUTE_CAPABILITY = "scientific:execute"

    def __init__(self, limits=None, *, state_journal_path=None, model_fabric=None, user_understanding=None):
        if model_fabric is None:
            raise ValueError("model_fabric_required_for_operational_agents")
        super().__init__(limits, state_journal_path=state_journal_path, model_fabric=model_fabric, user_understanding=user_understanding)
        self.system_fabric = CanonicalSystemFabric(identity_registry=self.identity_registry)
        self.router.system_fabric = self.system_fabric
        self.scientific_knowledge = ScientificKnowledgeFabric()
        self.scientific_fabric = ScientificFabric()
        branching_engine = getattr(self.hypersynth.universal_intelligence, "branching_engine", None)
        if branching_engine is not None:
            branching_engine.source_provider = lambda task: self.scientific_knowledge.research_context(limit=8)
            self.hypersynth.kernel.hypothesis_engine.branching_engine = branching_engine
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
            self.system_fabric.bind_agent_identity(identity, capabilities=("execute", self.MODEL_EXECUTE_CAPABILITY, self.SCIENTIFIC_EXECUTE_CAPABILITY))
        statuses = self.agent_runtime.start()
        status_ids = {item.agent_id for item in statuses}
        if not self.REQUIRED_AGENT_IDS.issubset(status_ids):
            self.agent_runtime.stop(); self.shutdown(); raise RuntimeError("primary_secondary_agents_missing")
        if not statuses or not all(item.state == "ONLINE" for item in statuses):
            self.agent_runtime.stop(); self.shutdown(); raise RuntimeError("agent_runtime_not_online")
        fabric_ids = set(self.agent_fabric.available())
        if not self.REQUIRED_AGENT_IDS.issubset(fabric_ids):
            self.agent_runtime.stop(); self.shutdown(); raise RuntimeError("operational_fabric_agents_missing")
        self.continuity = AgentContinuityScheduler(agent_runtime=self.agent_runtime, cycle_callback=self._continuity_cycle, interval_seconds=300.0, max_cycles_per_start=1000)
        self.continuity.start()
        self.audit.record("agent_runtime_online", agents=tuple(item.agent_id for item in statuses), states=tuple(item.state for item in statuses), required_agents=tuple(sorted(self.REQUIRED_AGENT_IDS)), operational_fabric=tuple(sorted(fabric_ids)), continuity=True, scientific_fabric=True)

    def discover_scientific_sources(self, query: str, *, providers=("pubmed", "arxiv", "crossref"), max_results: int = 8, email: str | None = None) -> tuple[str, ...]:
        """Discover only public/authorized metadata and add it to the research fabric."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("research_query_required")
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 50:
            raise ValueError("invalid_research_result_limit")
        names = tuple(dict.fromkeys(providers))
        found = []
        if "pubmed" in names:
            if not isinstance(email, str) or "@" not in email:
                raise ValueError("pubmed_email_required")
            found.extend(PubMedSourceProvider(email=email).search(query, retmax=max_results))
        if "arxiv" in names:
            found.extend(ArxivSourceProvider().search(query, max_results=max_results))
        if "crossref" in names:
            found.extend(CrossrefSourceProvider().search(query, rows=max_results))
        unique = tuple({source.source_id: source for source in found}.values())
        ids = self.scientific_knowledge.add_sources(unique)
        self.audit.record("scientific_sources_discovered", query_digest=sha256(query.strip().encode("utf-8")).hexdigest(), providers=names, source_ids=ids, count=len(ids))
        return ids

    def _continuity_cycle(self, exercise) -> None:
        """Run one bounded internal Primary -> Secondary -> Primary research exercise."""
        primary = self.router.get("noryx7-llm")
        secondary = self.router.get("noryx7-secondary")
        if primary is None or secondary is None:
            raise RuntimeError("continuity_agents_missing")
        self.agent_runtime.require_online(exercise.agent_id)
        execution_id = "continuity:" + exercise.exercise_id
        seed = TaskSpec(task_id=exercise.exercise_id, task_type="continuous_research", objective="Perform a bounded cross-agent research exercise using multiple evidence patterns; identify uncertainty and a falsifiable next step.", input="Review the currently authorized scientific knowledge context and produce one concise hypothesis with explicit uncertainty.", constraints={"continuity": True, "external_side_effects": False, "source_policy": "authorized_only"}, verification_requirements=("agent_result", "cross_agent_review"), risk_class="normal", execution_id=execution_id)
        reconciliation, check = self.hypersynth.collaboration.run(seed, primary, secondary)
        if not check.valid or not reconciliation.accepted:
            raise RuntimeError("continuity_reconciliation_failed")
        digest = sha256(reconciliation.output.encode("utf-8")).hexdigest()
        research_sources = self.scientific_knowledge.research_context(limit=8)
        hypothesis_id = None
        if research_sources:
            hypothesis = self.scientific_knowledge.formulate_hypothesis(hypothesis_id=f"{exercise.exercise_id}:hypothesis", statement=reconciliation.output[:2000], source_ids=(source.source_id for source in research_sources), confidence=0.5, falsifiers=("new authorized evidence contradicts the statement", "controlled experiment fails the predicted relationship"), experiment_plan=("define measurable prediction", "run a bounded reproducible experiment", "independently verify the result"))
            hypothesis_id = hypothesis.hypothesis_id
        self.audit.record("agent_continuity_exercise", exercise_id=exercise.exercise_id, execution_id=execution_id, agent_id=exercise.agent_id, interaction=(primary.agent_id, secondary.agent_id, primary.agent_id), completed=True, final_output_digest=digest, proposal_digest=reconciliation.proposal_digest, critique_digest=reconciliation.critique_digest, authorized_source_ids=tuple(source.source_id for source in research_sources), hypothesis_id=hypothesis_id, execution_authority="none", external_side_effects=False)

    def execute_scientific_experiment(self, task: TaskSpec, problem: PDEProblem, solver, *, agent_id: str = "noryx7-llm", hypothesis_id: str | None = None, experiment_id: str | None = None):
        """Execute a bounded scientific solver only after canonical identity/capability authorization."""
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        if not isinstance(problem, PDEProblem) or not callable(solver):
            raise ValueError("invalid_scientific_execution_request")
        agent = self.router.get(agent_id) if isinstance(agent_id, str) else None
        identity = getattr(agent, "identity", None) if agent is not None else None
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise PermissionError("scientific_agent_identity_invalid")
        self.system_fabric.authorize_agent(identity, self.SCIENTIFIC_EXECUTE_CAPABILITY)
        execution_id = task.execution_id or uuid4().hex
        result, verification = self.scientific_fabric.execute(task, problem, solver)
        result_digest = sha256(repr(result).encode("utf-8")).hexdigest()
        self.audit.record("scientific_execution", execution_id=execution_id, agent_id=agent_id, capability=self.SCIENTIFIC_EXECUTE_CAPABILITY, result_digest=result_digest, verified=verification.valid)
        if not verification.valid:
            self.system_fabric.record_execution(execution_id=execution_id, client_id=agent_id, phase="scientific_rejected", metadata={"task_id": task.task_id, "reason": verification.reason, "result_digest": result_digest})
            return result, verification, None
        self.system_fabric.record_execution(execution_id=execution_id, client_id=agent_id, phase="scientific_verified", metadata={"task_id": task.task_id, "result_digest": result_digest})
        admitted_experiment = None
        if hypothesis_id is not None:
            if not isinstance(hypothesis_id, str) or not hypothesis_id.strip():
                raise ValueError("invalid_hypothesis_id")
            admitted_experiment = self.scientific_knowledge.admit_experiment(ResearchExperiment(experiment_id=experiment_id or f"{execution_id}:experiment", hypothesis_id=hypothesis_id, method=result.method, inputs_digest=sha256(repr(problem).encode("utf-8")).hexdigest(), result_summary=f"residual={result.residual:.3e}; divergence={result.divergence_error:.3e}; conservation={result.conservation_error:.3e}", verified=True))
            self.audit.record("scientific_experiment_admitted", execution_id=execution_id, hypothesis_id=hypothesis_id, experiment_id=admitted_experiment.experiment_id)
        return result, verification, admitted_experiment

    def _record_canonical_execution(self, *, execution_id: str, phase: str, metadata) -> None:
        self.system_fabric.record_execution(execution_id=execution_id, client_id="noryx7-runtime", phase=phase, metadata=metadata)
        self.audit.record(f"canonical_system_execution_{phase}", execution_id=execution_id, phase=phase)

    def run_hypersynth(self, task, interaction_context=None):
        execution_id = getattr(task, "execution_id", None)
        if not isinstance(execution_id, str) or not execution_id:
            execution_id = uuid4().hex
            task = type(task)(task.task_id, task.task_type, task.objective, task.input, task.constraints, task.verification_requirements, task.risk_class, execution_id)
        self._record_canonical_execution(execution_id=execution_id, phase="runtime_received", metadata={"task_id": getattr(task, "task_id", ""), "task_type": getattr(task, "task_type", "")})
        result = super().run_hypersynth(task, interaction_context=interaction_context)
        if isinstance(result, dict) and result.get("status") == "completed":
            self._record_canonical_execution(execution_id=execution_id, phase="runtime_committed", metadata={"task_id": getattr(task, "task_id", ""), "verified": True, "orchestration_stage": result.get("orchestration_stage", "")})
        elif isinstance(result, dict):
            self._record_canonical_execution(execution_id=execution_id, phase="runtime_rejected", metadata={"task_id": getattr(task, "task_id", ""), "reason": result.get("reason", "runtime_rejected")})
        return result

    def admit_training_candidate(self, report: EvaluationReport) -> TrainingStage:
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
        if hasattr(self, "continuity"):
            self.continuity.stop()
        self.agent_runtime.stop()
        self.shutdown()
