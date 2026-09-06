import hashlib
import json
import time
from uuid import uuid4

from .actions import ActionGate
from .agents import DeterministicAgent
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
from .verification import VerificationEngine


class NORYXRuntime:
    """Controlled runtime: validate -> understand -> represent -> route -> plan -> execute -> verify -> commit."""

    def __init__(self, limits: RuntimeLimits | None = None):
        self.limits = limits or RuntimeLimits()
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.recovery = RecoveryController()
        self.security = SecurityBoundary(self.policy, self.verifier, recovery=self.recovery)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = MemoryStore(max_items=self.limits.max_memory_items)
        self.state = StateStore(max_commits=self.limits.max_memory_items)
        self.audit = AuditLog()
        self.identity_registry = IdentityRegistry()
        deterministic_identity, _ = AgentIdentityAuthority.generate("deterministic")
        self.identity_registry.register(deterministic_identity)
        self.router = ResourceRouter(identity_registry=self.identity_registry)
        self.router.register(DeterministicAgent(self.verifier, identity=deterministic_identity))
        self.decomposer = TaskDecomposer()
        self.hypersynth = HypersynthRuntime(
            verifier=self.verifier,
            router=self.router,
            audit=self.audit,
            limits=self.limits,
            memory=self.memory,
            recovery=self.recovery,
        )
        self._offline: OfflineRuntime | None = None

    def _principal_binding(self, agent_id: str) -> tuple[str, str]:
        """Return the trusted agent principal and its exact public-key fingerprint."""
        agent = self.router.route(agent_id)
        identity = getattr(agent, "identity", None)
        if not self.identity_registry.is_trusted(identity):
            raise PermissionError("agent_identity_untrusted")
        fingerprint = hashlib.sha256(identity.public_key).hexdigest()
        return identity.agent_id, fingerprint

    def configure_offline(self, *, cipher: AuthenticatedCipher, key_id: str,
                          snapshot_authenticator, clock=None) -> OfflineRuntime:
        """Install an explicit offline boundary using the same policy, verifier and recovery controller.

        The key provider remains outside the runtime; production deployments must inject a
        hardware/KMS-backed AuthenticatedCipher rather than the test-only in-memory provider.
        """
        bound_cipher = BoundAuthenticatedCipher(cipher, key_id=key_id)
        offline = OfflineRuntime(
            recovery=self.recovery,
            policy=PolicyOfflineAdapter(self.policy),
            verifier=VerificationOfflineAdapter(self.verifier),
            cipher=bound_cipher,
            clock=clock or (lambda: int(time.time())),
            snapshot_authenticator=snapshot_authenticator,
            max_snapshot_age=86_400,
        )
        self._offline = offline
        return offline

    @property
    def offline(self) -> OfflineRuntime | None:
        return self._offline

    def install_offline_snapshot(self, snapshot: OfflineSnapshot) -> None:
        if self._offline is None:
            raise RuntimeError("offline_not_configured")
        self._offline.install_snapshot(snapshot)

    @staticmethod
    def _offline_payload(task: TaskSpec) -> bytes:
        body = {"task_id": task.task_id, "task_type": task.task_type,
                "objective": task.objective, "input": task.input}
        try:
            payload = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("offline_payload_serialization_failed") from exc
        return payload

    def run_offline(self, task: TaskSpec, *, capability: str, local_executor):
        """Execute an already-authorized local operation without invoking cloud routing."""
        if self._offline is None:
            return {"status": "rejected", "reason": "offline_not_configured", "task_id": getattr(task, "task_id", None)}
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            return {"status": "rejected", "reason": "invalid_task", "task_id": getattr(task, "task_id", None)}
        if not isinstance(capability, str) or not capability.strip():
            return {"status": "rejected", "reason": "offline_capability_required", "task_id": task.task_id}
        if not callable(local_executor):
            return {"status": "rejected", "reason": "local_executor_required", "task_id": task.task_id}

        execution_id = task.execution_id or uuid4().hex
        principal_id, principal_key_fingerprint = self._principal_binding("deterministic")
        payload = self._offline_payload(task)
        execution = OfflineExecution(
            execution_id=execution_id,
            principal_id=principal_id,
            operation=task.task_type,
            capability=capability,
            payload_digest=hashlib.sha256(payload).hexdigest(),
            base_state_version=str(self.state.version),
        )

        committed = {}
        def commit(execution_record, result):
            verification = self.verifier.verify_output(result, stage="runtime_result")
            if not verification.is_well_formed() or not verification.valid:
                raise PermissionError("offline_result_unverified")
            state = NORYXState(
                input_digest=hashlib.sha256(str(task.input).encode("utf-8")).hexdigest(),
                goal=task.objective,
                subtasks=[task.task_id],
                final_answer=str(result),
                verification_results=[{"stage": verification.stage, "valid": verification.valid, "reason": verification.reason}],
                confidence=1.0,
                status="verified",
            )
            committed["state"] = self.state.commit(
                state, execution_id=execution_record.execution_id, task_id=task.task_id,
                principal_id=principal_id, principal_key_fingerprint=principal_key_fingerprint,
                verification_valid=verification.valid, verification_stage=verification.stage,
            )

        try:
            envelope = self._offline.execute(
                execution=execution,
                payload=payload,
                execute=lambda: local_executor(task),
                commit=commit,
            )
        except Exception as exc:
            self.audit.record("offline_execution_rejected", task_id=task.task_id,
                              execution_id=execution_id, reason=type(exc).__name__)
            return {"status": "rejected", "reason": str(exc), "task_id": task.task_id, "execution_id": execution_id}
        self.audit.record("offline_execution_committed", task_id=task.task_id,
                          execution_id=execution_id, sequence=envelope.sequence)
        return {"status": "completed", "task_id": task.task_id, "execution_id": execution_id,
                "state_commit": committed["state"], "sync_envelope": envelope,
                "offline_state": self._offline.state.value, "audit": self.audit.snapshot()}

    def _context_envelope(self, task: TaskSpec, interaction_context: InteractionContext, execution_id: str, principal_id: str) -> OrchestrationEnvelope:
        if not isinstance(interaction_context, InteractionContext):
            raise TypeError("interaction_context_required")
        envelope = OrchestrationEnvelope(
            request_id=task.task_id,
            principal_id=principal_id,
            operation=task.task_type,
            interaction_context=interaction_context,
        )
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.UNDERSTOOD)
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.REPRESENTED)
        return envelope

    @staticmethod
    def _plan_material(subtasks) -> str:
        return repr(tuple((x.subtask_id, x.task_type, x.objective) for x in subtasks))

    @staticmethod
    def _rejection(envelope, task_id, reason, audit, **extra):
        if envelope is not None and envelope.stage not in (OrchestrationStage.COMMITTED, OrchestrationStage.REJECTED):
            try:
                envelope, transition = OrchestrationCoordinator.reject(envelope)
                audit.record("orchestration_reject", task_id=task_id, stage=envelope.stage.value,
                             reason=reason, envelope_digest=transition.envelope_digest)
            except (TypeError, ValueError):
                audit.record("orchestration_reject_failure", task_id=task_id, reason=reason)
        result = {"status": "rejected", "reason": reason, "task_id": task_id}
        result.update(extra)
        if envelope is not None:
            result["orchestration_stage"] = envelope.stage.value
        return result

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
        try:
            principal_id, principal_key_fingerprint = self._principal_binding(agent_id)
        except (LookupError, PermissionError):
            return {"status": "rejected", "reason": "agent_identity_untrusted", "task_id": task_id}

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
            result = {"status": "rejected", "reason": "input_limit_exceeded"}
            self.audit.record("task_rejected", task_id=task_id, reason=result["reason"])
            return result
        if deadline_exceeded():
            self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
            return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}

        try:
            envelope = self._context_envelope(task, interaction_context, execution_id, principal_id)
            envelope = OrchestrationCoordinator.with_intent_digest(envelope, task.objective)
            self.audit.record("orchestration_context", task_id=task_id, context_id=interaction_context.context_id, envelope_digest=OrchestrationCoordinator.digest(envelope))
        except (TypeError, ValueError):
            self.audit.record("orchestration_rejection", task_id=task_id, reason="invalid_interaction_context")
            return {"status": "rejected", "reason": "invalid_interaction_context", "task_id": task_id}

        try:
            subtasks = self.decomposer.decompose(task)
            agent = self.router.route(agent_id)
            envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.ROUTED)
            envelope = OrchestrationCoordinator.with_plan_digest(envelope, self._plan_material(subtasks))
            envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.PLANNED)
        except LookupError:
            return self._rejection(envelope, task_id, "agent_unavailable", self.audit)
        except Exception:
            return self._rejection(envelope, task_id, "routing_failure", self.audit)
        if agent is None:
            return self._rejection(envelope, task_id, "agent_unavailable", self.audit)
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
            if not isinstance(result, AgentResult):
                return self._rejection(envelope, child.task_id, "malformed_agent_result", self.audit)
            if not result.is_well_formed():
                return self._rejection(envelope, child.task_id, "malformed_agent_result", self.audit)
            if result.agent_id != agent.agent_id:
                return self._rejection(envelope, child.task_id, "agent_identity_mismatch", self.audit)
            if result.task_id != child.task_id:
                return self._rejection(envelope, child.task_id, "task_identity_mismatch", self.audit)
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
            return self._rejection(envelope, task_id, "aggregate_verification_failed", self.audit, verification=failed)
        final_verification = self.verifier.verify_output(results[-1].output if results else None, stage="runtime_result")
        if not final_verification.valid:
            return self._rejection(envelope, task_id, "final_verification_failed", self.audit, verification=final_verification)
        verification_results = [
            {"stage": check.stage, "valid": check.valid, "reason": check.reason} for check in aggregate_verification
        ]
        verification_results.append({"stage": final_verification.stage, "valid": final_verification.valid, "reason": final_verification.reason})
        committed_state = NORYXState(
            input_digest=hashlib.sha256(str(task.input).encode("utf-8")).hexdigest(), goal=task.objective,
            subtasks=list(expected_task_ids), final_answer=str(results[-1].output) if results else "",
            verification_results=verification_results, confidence=1.0, status="verified")
        try:
            commit = self.recovery.run_if_normal(
                lambda: self.state.commit(committed_state, execution_id=execution_id, task_id=task_id,
                                          principal_id=principal_id, principal_key_fingerprint=principal_key_fingerprint,
                                          verification_valid=final_verification.valid, verification_stage=final_verification.stage),
                expected_epoch=recovery_epoch)
        except (TypeError, ValueError, PermissionError, MemoryError) as exc:
            self.audit.record("state_commit_failure", task_id=task_id, reason=type(exc).__name__)
            return self._rejection(envelope, task_id, "state_commit_failed", self.audit)
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.COMMITTED)
        self.audit.record("orchestration_commit", task_id=task_id, stage=envelope.stage.value,
                          context_id=interaction_context.context_id, execution_id=execution_id, state_sequence=commit.sequence,
                          principal_id=principal_id, principal_key_fingerprint=principal_key_fingerprint)
        return {"status": "completed", "results": tuple(results), "state_commit": commit,
                "orchestration_stage": envelope.stage.value, "audit": self.audit.snapshot()}

    def run_hypersynth(self, task: TaskSpec, interaction_context: InteractionContext | None = None):
        """Execute a task through the bounded HYPERSYNTH cognitive pipeline."""
        if interaction_context is None or not isinstance(interaction_context, InteractionContext):
            return {"status": "rejected", "reason": "interaction_context_required", "task_id": getattr(task, "task_id", None)}
        return self.hypersynth.run(task, interaction_context=interaction_context)
