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
from .interaction_context import InteractionContext
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

    def __init__(
        self,
        limits: RuntimeLimits | None = None,
        *,
        state_journal_path: str | None = None,
        model_fabric=None,
    ):
        self.limits = limits or RuntimeLimits()
        self._model_fabric = model_fabric
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.recovery = RecoveryController()
        self.security = SecurityBoundary(self.policy, self.verifier, recovery=self.recovery)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = MemoryStore(max_items=self.limits.max_memory_items)
        self.state_journal = StateJournal(state_journal_path, max_commits=self.limits.max_memory_items) if state_journal_path else None
        self.state = StateStore(max_commits=self.limits.max_memory_items, journal=self.state_journal)
        self.audit = AuditLog()
        self.identity_registry = IdentityRegistry()
        deterministic_identity, _ = AgentIdentityAuthority.generate("deterministic")
        self.identity_registry.register(deterministic_identity)
        self.router = ResourceRouter(identity_registry=self.identity_registry)
        self.router.register(DeterministicAgent(self.verifier, identity=deterministic_identity))

        if model_fabric is not None:
            llm_identity, _ = AgentIdentityAuthority.generate("noryx7-llm")
            self.identity_registry.register(llm_identity)
            self.router.register(
                LLMBackedAgent(
                    model_fabric,
                    verifier=self.verifier,
                    self_knowledge=SelfKnowledgeProvider(runtime=self),
                    identity=llm_identity,
                )
            )

        self.decomposer = TaskDecomposer()
        self.hypersynth = HypersynthRuntime(
            verifier=self.verifier,
            router=self.router,
            audit=self.audit,
            limits=self.limits,
            memory=self.memory,
            recovery=self.recovery,
        )
        self.capability_registry = self.hypersynth.tool_executor.capabilities
        self.tool_executor = self.hypersynth.tool_executor
        self.frontier_capabilities = self.hypersynth.frontier_capabilities
        self._offline: OfflineRuntime | None = None

    def configure_offline(
        self,
        *,
        cipher: AuthenticatedCipher,
        key_id: str,
        snapshot_authenticator,
        clock,
    ) -> None:
        """Configure the canonical fail-closed offline runtime."""
        self._offline = OfflineRuntime(
            recovery=self.recovery,
            policy=PolicyOfflineAdapter(self.policy),
            verifier=VerificationOfflineAdapter(self.verifier),
            cipher=BoundAuthenticatedCipher(cipher, key_id=key_id),
            clock=clock,
            snapshot_authenticator=snapshot_authenticator,
        )
        self.audit.record(
            "offline_runtime_configured",
            key_id=key_id,
        )

    @property
    def offline(self) -> OfflineRuntime | None:
        return self._offline

    def install_offline_snapshot(self, snapshot: OfflineSnapshot) -> None:
        if self._offline is None:
            raise RuntimeError("offline_not_configured")
        self._offline.install_snapshot(snapshot)
        self.audit.record(
            "offline_snapshot_installed",
            snapshot_id=snapshot.snapshot_id,
            principal_id=snapshot.principal_id,
        )

    def run_offline(
        self,
        task: TaskSpec,
        *,
        capability: str,
        local_executor,
    ) -> dict:
        """Execute one fail-closed offline task through the canonical runtime."""
        task_id = getattr(task, "task_id", None)
        execution_id = getattr(task, "execution_id", None) or str(uuid4())
        principal_id = execution_id

        if self._offline is None:
            return {
                "status": "rejected",
                "reason": "offline_not_configured",
                "task_id": task_id,
                "execution_id": execution_id,
            }

        try:
            payload = json.dumps(
                {
                    "task_id": task_id,
                    "task_type": getattr(task, "task_type", ""),
                    "objective": getattr(task, "objective", ""),
                    "input": getattr(task, "input", None),
                    "constraints": getattr(task, "constraints", {}),
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")

            payload_digest = hashlib.sha256(payload).hexdigest()

            snapshot = self._offline._snapshot
            if snapshot is None:
                raise RuntimeError("offline_snapshot_required")

            execution = OfflineExecution(
                execution_id=execution_id,
                principal_id=principal_id,
                operation=getattr(task, "task_type", "local-analysis"),
                capability=capability,
                payload_digest=payload_digest,
                base_state_version=snapshot.state_version,
            )

            committed = {}

            def commit(execution_spec, produced) -> None:
                state = NORYXState(
                    input_digest=payload_digest,
                    goal=getattr(task, "objective", ""),
                    subtasks=[],
                    selected_models=[],
                    hypotheses=[],
                    verification_results=[
                        {
                            "stage": "runtime_result",
                            "valid": True,
                            "reason": "offline_result_verified",
                        }
                    ],
                    confidence=1.0,
                    final_answer=str(produced),
                    status="verified",
                )

                principal_key_fingerprint = hashlib.sha256(
                    f"offline-principal:{execution_spec.principal_id}".encode("utf-8")
                ).hexdigest()

                state_commit = self.state.commit(
                    state,
                    execution_id=execution_spec.execution_id,
                    task_id=task_id,
                    verification_valid=True,
                    verification_stage="runtime_result",
                    principal_id=execution_spec.principal_id,
                    principal_key_fingerprint=principal_key_fingerprint,
                )
                committed["state_commit"] = state_commit

            sync_envelope = self._offline.execute(
                execution=execution,
                payload=payload,
                execute=lambda: local_executor(task),
                commit=commit,
            )

            return {
                "status": "completed",
                "task_id": task_id,
                "execution_id": execution_id,
                "state_commit": committed["state_commit"],
                "sync_envelope": sync_envelope,
            }

        except Exception as exc:
            reason = str(exc) or "offline_execution_failed"
            self.audit.record(
                "offline_execution_rejected",
                task_id=task_id,
                execution_id=execution_id,
                reason=reason,
            )
            return {
                "status": "rejected",
                "reason": reason,
                "task_id": task_id,
                "execution_id": execution_id,
            }

    def run_hypersynth(
        self,
        task: TaskSpec,
        interaction_context: InteractionContext | None = None,
    ):
        execution_id = getattr(task, "execution_id", None) or uuid4().hex
        if getattr(task, "execution_id", None) != execution_id:
            task = replace(task, execution_id=execution_id)

        recovery_state, _ = self.recovery.snapshot()
        if recovery_state.value != "normal":
            self.audit.record(
                "recovery_execution_denied",
                task_id=getattr(task, "task_id", None),
                execution_id=execution_id,
                reason="recovery_state_denies_execution",
            )
            return {
                "status": "rejected",
                "reason": "recovery_state_denies_execution",
                "task_id": getattr(task, "task_id", None),
                "execution_id": execution_id,
            }

        task_id = getattr(task, "task_id", None)
        envelope = None

        try:
            envelope = self._context_envelope(
                task,
                interaction_context,
                execution_id,
            )

            envelope = OrchestrationCoordinator.with_intent_digest(
                envelope,
                f"{task.task_type}|{task.objective}",
            )

            envelope, transition = OrchestrationCoordinator.transition(
                envelope,
                OrchestrationStage.ROUTED,
            )

            self.audit.record(
                "orchestration_transition",
                task_id=task_id,
                execution_id=execution_id,
                stage=envelope.stage.value,
                envelope_digest=transition.envelope_digest,
            )

            result = self.hypersynth.run(
                task,
                interaction_context=interaction_context,
                preferred_agent=(
                    "noryx7-llm"
                    if self._model_fabric is not None
                    else None
                ),
            )

            if not isinstance(result, dict):
                return self._rejection(
                    envelope,
                    task_id,
                    "malformed_hypersynth_result",
                    self.audit, execution_id=execution_id,
                )

            if result.get("execution_id") != execution_id:
                return self._rejection(
                    envelope,
                    task_id,
                    "task_identity_mismatch",
                    self.audit, execution_id=execution_id,
                )

            if result.get("status") != "completed":
                verification = result.get("verification")
                reason = "hypersynth_rejected"
                if isinstance(verification, VerificationResult):
                    reason = verification.reason or reason
                return self._rejection(
                    envelope,
                    task_id,
                    reason,
                    self.audit,
                    verification=verification, execution_id=execution_id,
                )

            verification = result.get("verification")

            if not (
                isinstance(verification, VerificationResult)
                and verification.is_well_formed()
                and verification.valid
                and verification.stage == "hypersynth_result"
            ):
                return self._rejection(
                    envelope,
                    task_id,
                    "invalid_hypersynth_verification",
                    self.audit,
                    verification=verification, execution_id=execution_id,
                )

            results = result.get("results")

            if not isinstance(results, tuple) or not results:
                return self._rejection(
                    envelope,
                    task_id,
                    "invalid_hypersynth_results",
                    self.audit, execution_id=execution_id,
                )

            final_result = results[-1]
            final_answer = getattr(final_result, "output", None)
            agent_id = getattr(final_result, "agent_id", None)

            if not isinstance(final_answer, str):
                return self._rejection(
                    envelope,
                    task_id,
                    "invalid_hypersynth_output",
                    self.audit, execution_id=execution_id,
                )

            runtime_verification = self.verifier.verify_output(
                final_answer,
                stage="runtime_result",
            )

            if not runtime_verification.valid:
                return self._rejection(
                    envelope,
                    task_id,
                    runtime_verification.reason or "runtime_verification_failed",
                    self.audit,
                    verification=runtime_verification, execution_id=execution_id,
                )

            plan_material = repr(result.get("plan", ""))

            if not plan_material.strip():
                plan_material = task.objective

            if len(plan_material.encode("utf-8")) > 2048:
                plan_material = plan_material.encode("utf-8")[:2048].decode(
                    "utf-8",
                    "ignore",
                )

            envelope = OrchestrationCoordinator.with_plan_digest(
                envelope,
                plan_material,
            )

            envelope, transition = OrchestrationCoordinator.transition(
                envelope,
                OrchestrationStage.PLANNED,
            )

            self.audit.record(
                "orchestration_transition",
                task_id=task_id,
                execution_id=execution_id,
                stage=envelope.stage.value,
                envelope_digest=transition.envelope_digest,
            )

            envelope, transition = OrchestrationCoordinator.transition(
                envelope,
                OrchestrationStage.EXECUTING,
            )

            self.audit.record(
                "orchestration_transition",
                task_id=task_id,
                execution_id=execution_id,
                stage=envelope.stage.value,
                envelope_digest=transition.envelope_digest,
            )

            envelope, transition = OrchestrationCoordinator.transition(
                envelope,
                OrchestrationStage.VERIFYING,
            )

            self.audit.record(
                "orchestration_transition",
                task_id=task_id,
                execution_id=execution_id,
                stage=envelope.stage.value,
                envelope_digest=transition.envelope_digest,
            )

            if not isinstance(agent_id, str) or not agent_id.strip():
                return self._rejection(
                    envelope,
                    task_id,
                    "agent_identity_missing",
                    self.audit,
                    verification=runtime_verification, execution_id=execution_id,
                )

            principal_id, principal_key_fingerprint = self._principal_binding(
                agent_id
            )

            verification_results = [
                {
                    "stage": verification.stage,
                    "valid": verification.valid,
                    "reason": verification.reason,
                },
                {
                    "stage": runtime_verification.stage,
                    "valid": runtime_verification.valid,
                    "reason": runtime_verification.reason,
                },
            ]

            reflection = result.get("reflection")
            confidence = getattr(reflection, "confidence", 1.0)

            if isinstance(confidence, bool) or not isinstance(
                confidence,
                (int, float),
            ):
                confidence = 1.0

            confidence = max(0.0, min(1.0, float(confidence)))

            state = NORYXState(
                input_digest=hashlib.sha256(
                    str(task.input).encode("utf-8")
                ).hexdigest(),
                goal=task.objective,
                subtasks=[
                    getattr(item, "task_id", task_id)
                    for item in results
                ],
                selected_models=sorted(
                    {
                        getattr(item, "agent_id", agent_id)
                        for item in results
                        if isinstance(
                            getattr(item, "agent_id", agent_id),
                            str,
                        )
                    }
                ),
                hypotheses=[],
                verification_results=verification_results,
                confidence=confidence,
                final_answer=final_answer,
                status="verified",
            )

            try:
                commit = self.state.commit(
                    state,
                    execution_id=execution_id,
                    task_id=task_id,
                    principal_id=principal_id,
                    principal_key_fingerprint=principal_key_fingerprint,
                    verification_valid=True,
                    verification_stage="runtime_result",
                )
            except Exception as exc:
                return self._rejection(
                    envelope,
                    task_id,
                    "state_commit_failed",
                    self.audit,
                    error=type(exc).__name__, execution_id=execution_id,
                )

            envelope, transition = OrchestrationCoordinator.transition(
                envelope,
                OrchestrationStage.COMMITTED,
            )

            self.audit.record(
                "state_commit",
                task_id=task_id,
                execution_id=execution_id,
                sequence=commit.sequence,
            )

            self.audit.record(
                "orchestration_committed",
                task_id=task_id,
                execution_id=execution_id,
                envelope_digest=transition.envelope_digest,
            )

            return {
                **result,
                "status": "completed",
                "task_id": task_id,
                "execution_id": execution_id,
                "result": final_answer,
                "verification": runtime_verification,
                "hypersynth_verification": verification,
                "orchestration_stage": envelope.stage.value,
                "state_commit": commit,
                "audit": self.audit.snapshot(),
            }

        except (PermissionError, LookupError) as exc:
            return self._rejection(
                envelope,
                task_id,
                "agent_identity_untrusted",
                self.audit,
                error=type(exc).__name__, execution_id=execution_id,
            )

        except Exception as exc:
            return self._rejection(
                envelope,
                task_id,
                "hypersynth_runtime_integration_failed",
                self.audit,
                error=type(exc).__name__, execution_id=execution_id,
            )

    @staticmethod
    def _default_interaction_context(task: TaskSpec) -> InteractionContext:
        context_id = hashlib.sha256(
            f"runtime:{getattr(task, "task_id", "")}".encode("utf-8")
        ).hexdigest()
        return InteractionContext(
            profile_id="runtime",
            signals=(),
            context_id=context_id,
        )

    def _context_envelope(
        self,
        task: TaskSpec,
        interaction_context: InteractionContext | None,
        execution_id: str,
        principal_id: str | None = None,
    ) -> OrchestrationEnvelope:
        if interaction_context is None:
            interaction_context = self._default_interaction_context(task)

        if not isinstance(interaction_context, InteractionContext):
            raise TypeError("interaction_context_required")

        interaction_context.as_prompt_context()

        principal = (
            principal_id
            or getattr(task, "principal_id", None)
            or "deterministic"
        )

        envelope = OrchestrationEnvelope(
            request_id=task.task_id,
            principal_id=principal,
            operation=task.task_type,
            interaction_context=interaction_context,
        )

        envelope, _ = OrchestrationCoordinator.transition(
            envelope,
            OrchestrationStage.UNDERSTOOD,
        )
        envelope, _ = OrchestrationCoordinator.transition(
            envelope,
            OrchestrationStage.REPRESENTED,
        )

        return envelope

    def _principal_binding(
        self,
        agent_id: str,
    ) -> tuple[str, str | None]:
        agent = self.router.route(agent_id)

        registry = getattr(self.router, "identity_registry", None)

        if registry is None:
            return agent_id, None

        identity = getattr(agent, "identity", None)

        if not registry.is_trusted(identity):
            raise PermissionError("agent_identity_untrusted")

        fingerprint = hashlib.sha256(
            identity.public_key
        ).hexdigest()

        return identity.agent_id, fingerprint

    def _rejection(
        self,
        envelope: OrchestrationEnvelope | None,
        task_id: str | None,
        reason: str,
        audit: AuditLog,
        verification: VerificationResult | None = None,
        execution_id: str | None = None,
        error: str | None = None,
    ) -> dict:
        if not isinstance(reason, str) or not reason.strip():
            reason = "controlled_runtime_failure"

        orchestration_stage = OrchestrationStage.REJECTED.value

        if envelope is not None:
            try:
                if envelope.stage not in (
                    OrchestrationStage.COMMITTED,
                    OrchestrationStage.REJECTED,
                ):
                    envelope, _ = OrchestrationCoordinator.reject(envelope)
                orchestration_stage = envelope.stage.value
            except Exception:
                orchestration_stage = OrchestrationStage.REJECTED.value

        audit.record(
            "orchestration_rejection",
            task_id=task_id,
            reason=reason,
            orchestration_stage=orchestration_stage,
        )

        result = {
            "status": "rejected",
            "reason": reason,
            "task_id": task_id,
            "execution_id": execution_id,
            "orchestration_stage": orchestration_stage,
        }
        if error is not None:
            result["error"] = error
        if verification is not None:
            result["verification"] = verification
        return result

    @staticmethod
    def _plan_material(subtasks) -> str:
        if subtasks is None:
            raise ValueError("subtasks_required")

        try:
            material = json.dumps(
                [
                    {
                        "task_id": getattr(item, "task_id", ""),
                        "task_type": getattr(item, "task_type", ""),
                        "objective": getattr(item, "objective", ""),
                        "input": getattr(item, "input", ""),
                        "constraints": getattr(item, "constraints", {}),
                        "risk_class": getattr(item, "risk_class", ""),
                    }
                    for item in subtasks
                ],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
        except Exception as exc:
            raise ValueError("plan_material_invalid") from exc

        if not material.strip():
            raise ValueError("plan_material_empty")

        return material

    def run(self, task: TaskSpec, agent_id: str = "deterministic", interaction_context: InteractionContext | None = None):
        started = time.monotonic()
        deadline = started + self.limits.max_task_seconds
        task_id = getattr(task, "task_id", None)
        execution_id = getattr(task, "execution_id", "") or uuid4().hex
        envelope = None
        recovery_state, recovery_epoch = self.recovery.snapshot()
        if recovery_state.value != "normal":
            self.audit.record("recovery_execution_denied", task_id=task_id, reason="recovery_state_denies_execution")
            return {"status": "rejected", "reason": "recovery_state_denies_execution", "task_id": task_id}
        def deadline_exceeded() -> bool:
            return time.monotonic() > deadline
        try:
            task_check = self.verifier.verify_task(task)
        except Exception:
            self.audit.record("task_verification_failure", task_id=task_id, reason="controlled_runtime_failure")
            return {"status": "rejected", "reason": "controlled_runtime_failure", "task_id": task_id}
        self.audit.record("task_verification", task_id=task_id, valid=task_check.valid, reason=task_check.reason)
        if not task_check.valid:
            return {"status": "rejected", "reason": task_check.reason, "verification": task_check}
        if not self.limits.validate_input(task.input):
            verification = VerificationResult(
                False,
                "runtime_result",
                "input_limit_exceeded",
            )
            result = {
                "status": "rejected",
                "reason": "input_limit_exceeded",
                "task_id": task_id,
                "verification": verification,
            }
            self.audit.record("task_rejected", task_id=task_id, reason=result["reason"])
            return result
        if deadline_exceeded():
            self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
            return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}
        try:
            agent = self.router.route(agent_id)
            principal_id, principal_key_fingerprint = self._principal_binding(agent_id)
        except LookupError:
            return {"status": "rejected", "reason": "agent_unavailable", "task_id": task_id}
        except PermissionError:
            return {"status": "rejected", "reason": "agent_identity_untrusted", "task_id": task_id}
        if agent is None:
            return {"status": "rejected", "reason": "agent_unavailable", "task_id": task_id}
        try:
            envelope = self._context_envelope(task, interaction_context, execution_id, principal_id)
            envelope = OrchestrationCoordinator.with_intent_digest(envelope, task.objective)
            self.audit.record("orchestration_context", task_id=task_id, context_id=envelope.interaction_context.context_id,
                              envelope_digest=OrchestrationCoordinator.digest(envelope))
        except (TypeError, ValueError):
            self.audit.record("orchestration_rejection", task_id=task_id, reason="invalid_interaction_context")
            return {"status": "rejected", "reason": "invalid_interaction_context", "task_id": task_id}
        try:
            subtasks = self.decomposer.decompose(task)
            envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.ROUTED)
            envelope = OrchestrationCoordinator.with_plan_digest(envelope, self._plan_material(subtasks))
            envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.PLANNED)
        except LookupError:
            return self._rejection(envelope, task_id, "agent_unavailable", self.audit)
        except Exception:
            return self._rejection(envelope, task_id, "routing_failure", self.audit)
        if len(subtasks) > self.limits.max_actions_per_task:
            return self._rejection(envelope, task_id, "max_actions_per_task_exceeded", self.audit)
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.EXECUTING)
        results = []
        for subtask in subtasks:
            if deadline_exceeded():
                return self._rejection(envelope, task_id, "max_task_seconds_exceeded", self.audit)
            child = TaskSpec(subtask.subtask_id, subtask.task_type, subtask.objective, task.input,
                             task.constraints, task.verification_requirements, task.risk_class, execution_id)
            action = ActionSpec("act:" + child.task_id, "compute", execution_id=child.execution_id, risk_class=child.risk_class)
            try:
                decision, result = self.recovery.run_if_normal(
                    lambda: self.action_gate.authorize_and_execute(
                        action, lambda: agent.run(child), calls_used=len(results), execution_id=child.execution_id),
                    expected_epoch=recovery_epoch,
                )
            except PermissionError as exc:
                return self._rejection(envelope, child.task_id, str(exc), self.audit)
            except Exception:
                return self._rejection(envelope, child.task_id, "action_execution_failure", self.audit)
            self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
            if not decision.allowed:
                return self._rejection(envelope, child.task_id, decision.reason, self.audit, verification=decision.verification)
            if not isinstance(result, AgentResult) or not result.is_well_formed():
                return self._rejection(envelope, child.task_id, "malformed_agent_result", self.audit)
            if result.agent_id != agent.agent_id:
                verification = VerificationResult(
                    False,
                    "agent_result",
                    "agent_identity_mismatch",
                )
                return self._rejection(
                    envelope,
                    child.task_id,
                    "agent_identity_mismatch",
                    self.audit,
                    verification=verification,
                )
            if result.task_id != child.task_id:
                verification = VerificationResult(
                    False,
                    "agent_result",
                    "task_identity_mismatch",
                )
                return self._rejection(
                    envelope,
                    child.task_id,
                    "task_identity_mismatch",
                    self.audit,
                    verification=verification,
                )
            if result.execution_id != execution_id:
                return self._rejection(envelope, child.task_id, "execution_identity_mismatch", self.audit)
            if result.status != "completed":
                return self._rejection(envelope, child.task_id, "invalid_result_status", self.audit)
            if result.verification is None or not result.verification.is_well_formed() or not result.verification.valid:
                return self._rejection(envelope, child.task_id, "unverified_agent_result", self.audit)
            if result.verification.stage != "agent_result":
                return self._rejection(envelope, child.task_id, "verification_stage_mismatch", self.audit)
            if deadline_exceeded():
                return self._rejection(envelope, child.task_id, "max_task_seconds_exceeded", self.audit)
            output = result.output
            if not self.limits.validate_output(output) or not self.limits.validate_output_items(output):
                return self._rejection(envelope, child.task_id, "output_limit_exceeded", self.audit)
            runtime_verification = self.verifier.verify_output(output, stage="runtime_result")
            if not runtime_verification.valid:
                return self._rejection(envelope, child.task_id, "runtime_output_verification_failed", self.audit, verification=runtime_verification)
            results.append(result)
        if deadline_exceeded():
            return self._rejection(envelope, task_id, "max_task_seconds_exceeded", self.audit)
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.VERIFYING)
        expected_task_ids = tuple(x.subtask_id for x in subtasks)
        aggregate_verification = self.verifier.verify_agent_results(
            results, expected_agent_id=agent.agent_id, expected_execution_id=execution_id,
            expected_task_ids=expected_task_ids)
        if not aggregate_verification or not all(check.valid for check in aggregate_verification):
            failed = next((check for check in aggregate_verification if not check.valid),
                          VerificationResult(False, "runtime_results", "aggregate_verification_failed"))
            return self._rejection(envelope, task_id, failed.reason, self.audit, verification=failed)
        final_answer = results[-1].output if results else ""
        state = NORYXState(
            input_digest=hashlib.sha256(str(task.input).encode("utf-8")).hexdigest(),
            goal=task.objective,
            subtasks=[x.subtask_id for x in subtasks],
            selected_models=[agent_id],
            verification_results=[{"stage": check.stage, "valid": check.valid, "reason": check.reason} for check in aggregate_verification],
            confidence=1.0,
            final_answer=str(final_answer),
            status="verified",
        )
        try:
            commit = self.state.commit(
                state, execution_id=execution_id, task_id=task_id,
                principal_id=principal_id, principal_key_fingerprint=principal_key_fingerprint,
                verification_valid=True, verification_stage="runtime_result",
            )
            envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.COMMITTED)
        except Exception as exc:
            return self._rejection(envelope, task_id, "state_commit_failed", self.audit, error=type(exc).__name__)
        self.audit.record("state_commit", task_id=task_id, execution_id=execution_id, sequence=commit.sequence)
        return {"status": "completed", "task_id": task_id, "execution_id": execution_id,
                "result": final_answer, "results": tuple(results),
                "verification": aggregate_verification,
                "orchestration_stage": envelope.stage.value, "state_commit": commit,
                "audit": self.audit.snapshot()}
