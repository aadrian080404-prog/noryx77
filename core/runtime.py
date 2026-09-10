import hashlib
import json
from dataclasses import replace
import time
from uuid import uuid4

from .actions import ActionGate
from .agents import DeterministicAgent
from .llm.agent import LLMBackedAgent
from .llm.self_knowledge import SelfKnowledgeProvider
from .audit import AuditLog
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .crypto import AuthenticatedCipher
from .decomposition import TaskDecomposer
from .hypersynth_runtime import HypersynthRuntime
from .identity import AgentIdentityAuthority, IdentityRegistry
from .interaction_context import InteractionContext, build_interaction_context
from .user_understanding import UnderstandingConsent, UserContent, UserUnderstandingEngine
from .limits import RuntimeLimits
from .memory import MemoryStore
from .offline import OfflineExecution, OfflineRuntime, OfflineSnapshot
from .offline_adapters import BoundAuthenticatedCipher, PolicyOfflineAdapter, VerificationOfflineAdapter
from .orchestration import OrchestrationCoordinator, OrchestrationEnvelope, OrchestrationStage
from .policy import PolicyEngine
from .recovery import RecoveryController
from .router import ResourceRouter
from .security import SecurityBoundary
from .state import NORYXState, StateStore
from .state_journal import StateJournal
from .verification import VerificationEngine


class NORYXRuntime:
    """Controlled runtime: validate -> understand -> represent -> route -> plan -> execute -> verify -> commit."""
    def __init__(self, limits: RuntimeLimits | None = None, *, state_journal_path: str | None = None, model_fabric=None, user_understanding: UserUnderstandingEngine | None = None):
        self.limits = limits or RuntimeLimits(); self._model_fabric = model_fabric
        if user_understanding is not None and not isinstance(user_understanding, UserUnderstandingEngine): raise TypeError("invalid_user_understanding_engine")
        self.user_understanding = user_understanding; self.verifier = VerificationEngine(); self.policy = PolicyEngine(); self.recovery = RecoveryController(); self.security = SecurityBoundary(self.policy, self.verifier, recovery=self.recovery); self.action_gate = ActionGate(self.policy, self.security, self.limits); self.memory = MemoryStore(max_items=self.limits.max_memory_items); self.state_journal = StateJournal(state_journal_path, max_commits=self.limits.max_memory_items) if state_journal_path else None; self.state = StateStore(max_commits=self.limits.max_memory_items, journal=self.state_journal); self.audit = AuditLog(); self.identity_registry = IdentityRegistry(); deterministic_identity, _ = AgentIdentityAuthority.generate("deterministic"); self.identity_registry.register(deterministic_identity); self.router = ResourceRouter(identity_registry=self.identity_registry); self.router.register(DeterministicAgent(self.verifier, identity=deterministic_identity))
        if model_fabric is not None:
            llm_identity, _ = AgentIdentityAuthority.generate("noryx7-llm"); self.identity_registry.register(llm_identity); self.router.register(LLMBackedAgent(model_fabric, verifier=self.verifier, self_knowledge=SelfKnowledgeProvider(runtime=self), identity=llm_identity))
        self.decomposer = TaskDecomposer(); self.hypersynth = HypersynthRuntime(verifier=self.verifier, router=self.router, audit=self.audit, limits=self.limits, memory=self.memory, recovery=self.recovery); self.capability_registry = self.hypersynth.tool_executor.capabilities; self.tool_executor = self.hypersynth.tool_executor; self.frontier_capabilities = self.hypersynth.frontier_capabilities; self._offline = None; self._closed = False

    def shutdown(self) -> None:
        if self._closed: return
        self._closed = True; journal = self.state_journal
        if journal is not None: journal.close()
        self.audit.record("runtime_shutdown", state_journal_closed=journal is not None)

    def configure_offline(self, *, cipher: AuthenticatedCipher, key_id: str, snapshot_authenticator, clock) -> None:
        self._offline = OfflineRuntime(recovery=self.recovery, policy=PolicyOfflineAdapter(self.policy), verifier=VerificationOfflineAdapter(self.verifier), cipher=BoundAuthenticatedCipher(cipher, key_id=key_id), clock=clock, snapshot_authenticator=snapshot_authenticator); self.audit.record("offline_runtime_configured", key_id=key_id)

    @property
    def offline(self): return self._offline

    def install_offline_snapshot(self, snapshot: OfflineSnapshot) -> None:
        if self._offline is None: raise RuntimeError("offline_not_configured")
        self._offline.install_snapshot(snapshot); self.audit.record("offline_snapshot_installed", snapshot_id=snapshot.snapshot_id, principal_id=snapshot.principal_id)

    def run_offline(self, task: TaskSpec, *, capability: str, local_executor) -> dict:
        task_id = getattr(task,"task_id",None); execution_id = getattr(task,"execution_id",None) or str(uuid4()); principal_id = execution_id
        if self._offline is None: return {"status":"rejected","reason":"offline_not_configured","task_id":task_id,"execution_id":execution_id}
        try:
            payload = json.dumps({"task_id":task_id,"task_type":getattr(task,"task_type",""),"objective":getattr(task,"objective",""),"input":getattr(task,"input",None),"constraints":getattr(task,"constraints",{})}, sort_keys=True, separators=(",",":"), ensure_ascii=False, default=str).encode("utf-8"); payload_digest = hashlib.sha256(payload).hexdigest(); snapshot = self._offline._snapshot
            if snapshot is None: raise RuntimeError("offline_snapshot_required")
            execution = OfflineExecution(execution_id=execution_id, principal_id=principal_id, operation=getattr(task,"task_type","local-analysis"), capability=capability, payload_digest=payload_digest, base_state_version=snapshot.state_version); committed = {}
            def commit(execution_spec, produced):
                state = NORYXState(input_digest=payload_digest, goal=getattr(task,"objective",""), subtasks=[], selected_models=[], hypotheses=[], verification_results=[{"stage":"runtime_result","valid":True,"reason":"offline_result_verified"}], confidence=1.0, final_answer=str(produced), status="verified")
                principal_key_fingerprint = hashlib.sha256(f"offline-principal:{execution_spec.principal_id}".encode("utf-8")).hexdigest(); committed["state_commit"] = self.state.commit(state, execution_id=execution_spec.execution_id, task_id=task_id, verification_valid=True, verification_stage="runtime_result", principal_id=execution_spec.principal_id, principal_key_fingerprint=principal_key_fingerprint)
            sync_envelope = self._offline.execute(execution=execution, payload=payload, execute=lambda: local_executor(task), commit=commit)
            return {"status":"completed","task_id":task_id,"execution_id":execution_id,"state_commit":committed["state_commit"],"sync_envelope":sync_envelope}
        except Exception as exc:
            reason = str(exc) or "offline_execution_failed"; self.audit.record("offline_execution_rejected", task_id=task_id, execution_id=execution_id, reason=reason); return {"status":"rejected","reason":reason,"task_id":task_id,"execution_id":execution_id}

    def run(self, task: TaskSpec, *, agent_id: str | None = None, interaction_context: InteractionContext | None = None) -> dict:
        """Legacy direct runtime entrypoint routed through the bounded HYPERSYNTH facade."""
        if not isinstance(task, TaskSpec): return {"status":"rejected","reason":"invalid_task_spec","task_id":getattr(task,"task_id",None),"execution_id":getattr(task,"execution_id",None),"verification":VerificationResult(False,"contract","invalid_task_spec"),"orchestration_stage":OrchestrationStage.REJECTED.value}
        if agent_id is not None and (not isinstance(agent_id,str) or not agent_id.strip()): return {"status":"rejected","reason":"invalid_agent_id","task_id":task.task_id,"execution_id":task.execution_id,"verification":VerificationResult(False,"identity","invalid_agent_id"),"orchestration_stage":OrchestrationStage.REJECTED.value}
        if self.hypersynth.router is not self.router:
            self.hypersynth.router = self.router
            self.hypersynth.kernel.router = self.router
            from .supervisor import AgentSupervisor
            self.hypersynth.kernel.supervisor = AgentSupervisor(self.router, self.verifier, audit=self.audit)
        result = self.hypersynth.run(task, interaction_context=interaction_context, preferred_agent=agent_id) if agent_id is not None else self.hypersynth.run(task, interaction_context=interaction_context)
        if not isinstance(result,dict): return {"status":"rejected","reason":"malformed_hypersynth_result","task_id":task.task_id,"execution_id":task.execution_id,"verification":VerificationResult(False,"runtime","malformed_hypersynth_result"),"orchestration_stage":OrchestrationStage.REJECTED.value}
        result = dict(result)
        if result.get("status") == "rejected":
            verification = result.get("verification")
            reason = getattr(verification, "reason", None) or result.get("reason") or "hypersynth_execution_rejected"
            # Preserve the historical public reason strings of NORYXRuntime.run
            # without weakening the canonical HYPERSYNTH verification vocabulary.
            legacy_reasons = {
                "execution_failure": "execution failure",
                "task_id_mismatch": "task_identity_mismatch",
                "agent_not_completed": "invalid_result_status",
                "invalid_agent_result": "malformed_agent_result",
                "preferred_agent_unavailable": "agent_unavailable",
            }
            reason = legacy_reasons.get(reason, reason)
            result["reason"] = reason
            if isinstance(verification, VerificationResult) and verification.reason != reason:
                result["verification"] = VerificationResult(verification.valid, verification.stage, reason, verification.details)
            result.setdefault("orchestration_stage", OrchestrationStage.REJECTED.value)
        else:
            result.setdefault("orchestration_stage", OrchestrationStage.COMMITTED.value)
        return result

    def run_hypersynth(self, task: TaskSpec, interaction_context: InteractionContext | None = None):
        execution_id = getattr(task,"execution_id",None) or uuid4().hex
        if getattr(task,"execution_id",None) != execution_id: task = replace(task, execution_id=execution_id)
        recovery_state, _ = self.recovery.snapshot()
        if recovery_state.value != "normal":
            self.audit.record("recovery_execution_denied", task_id=getattr(task,"task_id",None), execution_id=execution_id, reason="recovery_state_denies_execution"); return {"status":"rejected","reason":"recovery_state_denies_execution","task_id":getattr(task,"task_id",None),"execution_id":execution_id}
        task_id = getattr(task,"task_id",None); envelope = None
        try:
            if interaction_context is None and self.user_understanding is not None:
                content = UserContent(content_id=task_id or execution_id, text=str(getattr(task,"input","")), source="runtime_task_input"); profile = self.user_understanding.build_profile((content,)); interaction_context = build_interaction_context(profile); self.audit.record("user_understanding_derived", task_id=task_id, execution_id=execution_id, profile_id=profile.profile_id, context_id=interaction_context.context_id, consent=self.user_understanding.consent.value)
            envelope = self._context_envelope(task, interaction_context, execution_id); envelope = OrchestrationCoordinator.with_intent_digest(envelope, f"{task.task_type}|{task.objective}")
            envelope, transition = OrchestrationCoordinator.transition(envelope, OrchestrationStage.UNDERSTOOD); self.audit.record("orchestration_transition", task_id=task_id, execution_id=execution_id, stage=envelope.stage.value, envelope_digest=transition.envelope_digest)
            envelope, transition = OrchestrationCoordinator.transition(envelope, OrchestrationStage.REPRESENTED); self.audit.record("orchestration_transition", task_id=task_id, execution_id=execution_id, stage=envelope.stage.value, envelope_digest=transition.envelope_digest)
            envelope, transition = OrchestrationCoordinator.transition(envelope, OrchestrationStage.ROUTED); self.audit.record("orchestration_transition", task_id=task_id, execution_id=execution_id, stage=envelope.stage.value, envelope_digest=transition.envelope_digest)
            result = self.hypersynth.run(task, interaction_context=interaction_context, preferred_agent=("noryx7-llm" if self._model_fabric is not None else None))
            if not isinstance(result,dict): return self._rejection(envelope,task_id,"malformed_hypersynth_result",self.audit,execution_id=execution_id)
            if result.get("execution_id") != execution_id: return self._rejection(envelope,task_id,"task_identity_mismatch",self.audit,execution_id=execution_id)
            if result.get("status") != "completed":
                verification=result.get("verification"); reason=verification.reason if isinstance(verification,VerificationResult) and verification.reason else "hypersynth_rejected"; return self._rejection(envelope,task_id,reason,self.audit,verification=verification,execution_id=execution_id)
            verification=result.get("verification")
            if not (isinstance(verification,VerificationResult) and verification.is_well_formed() and verification.valid and verification.stage=="hypersynth_result"): return self._rejection(envelope,task_id,"invalid_hypersynth_verification",self.audit,verification=verification,execution_id=execution_id)
            result["runtime_verified"]=True; result["execution_id"]=execution_id; result["runtime_state"]="committed"; self.audit.record("runtime_result_verified",task_id=task_id,execution_id=execution_id,verification_stage=verification.stage); return result
        except Exception as exc: return self._rejection(envelope,task_id,str(exc) or "runtime_execution_failed",self.audit,execution_id=execution_id)

    def _context_envelope(self, task, interaction_context, execution_id):
        return OrchestrationEnvelope(envelope_id=uuid4().hex, task_id=task.task_id, execution_id=execution_id, stage=OrchestrationStage.RECEIVED, intent_digest=hashlib.sha256(f"{task.task_type}|{task.objective}".encode("utf-8")).hexdigest(), interaction_context_id=(interaction_context.context_id if interaction_context else None))

    @staticmethod
    def _rejection(envelope, task_id, reason, audit, *, verification=None, execution_id=None):
        audit.record("runtime_rejected", task_id=task_id, execution_id=execution_id, reason=reason, verification_stage=getattr(verification,"stage",None)); return {"status":"rejected","task_id":task_id,"execution_id":execution_id,"reason":reason,"verification":verification,"orchestration_stage":OrchestrationStage.REJECTED.value}
