import hashlib
import time
from uuid import uuid4

from .actions import ActionGate
from .agents import DeterministicAgent
from .audit import AuditLog
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .decomposition import TaskDecomposer
from .hypersynth_runtime import HypersynthRuntime
from .interaction_context import InteractionContext
from .limits import RuntimeLimits
from .memory import MemoryStore
from .orchestration import OrchestrationCoordinator, OrchestrationEnvelope, OrchestrationStage
from .policy import PolicyEngine
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
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.memory = MemoryStore(max_items=self.limits.max_memory_items)
        self.state = StateStore(max_commits=self.limits.max_memory_items)
        self.audit = AuditLog()
        self.router = ResourceRouter()
        self.router.register(DeterministicAgent(self.verifier))
        self.decomposer = TaskDecomposer()
        self.hypersynth = HypersynthRuntime(
            verifier=self.verifier,
            router=self.router,
            audit=self.audit,
            limits=self.limits,
            memory=self.memory,
        )

    def _context_envelope(self, task: TaskSpec, interaction_context: InteractionContext, execution_id: str) -> OrchestrationEnvelope:
        if not isinstance(interaction_context, InteractionContext):
            raise TypeError("interaction_context_required")
        envelope = OrchestrationEnvelope(
            request_id=task.task_id,
            principal_id=execution_id,
            operation=task.task_type,
            interaction_context=interaction_context,
        )
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.UNDERSTOOD)
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.REPRESENTED)
        return envelope

    @staticmethod
    def _plan_material(subtasks) -> str:
        return repr(tuple((x.subtask_id, x.task_type, x.objective) for x in subtasks))

    def run(self, task: TaskSpec, agent_id: str = "deterministic", interaction_context: InteractionContext | None = None):
        started = time.monotonic()
        deadline = started + self.limits.max_task_seconds
        task_id = getattr(task, "task_id", None)
        execution_id = getattr(task, "execution_id", "") or uuid4().hex

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
            envelope = self._context_envelope(task, interaction_context, execution_id)
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
            self.audit.record("routing_failure", task_id=task_id, error="agent_unavailable")
            return {"status": "rejected", "reason": "agent_unavailable", "task_id": task_id}
        except Exception:
            self.audit.record("routing_failure", task_id=task_id, error="routing_failure")
            return {"status": "rejected", "reason": "routing_failure"}
        if agent is None:
            self.audit.record("routing_failure", task_id=task_id, error="agent_unavailable")
            return {"status": "rejected", "reason": "agent_unavailable", "task_id": task_id}

        if len(subtasks) > self.limits.max_actions_per_task:
            self.audit.record("action_limit", task_id=task_id, allowed=False, reason="max_actions_per_task_exceeded")
            return {"status": "rejected", "reason": "max_actions_per_task_exceeded", "task_id": task_id}

        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.EXECUTING)
        results = []
        for subtask in subtasks:
            if deadline_exceeded():
                self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
                return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}
            child = TaskSpec(subtask.subtask_id, subtask.task_type, subtask.objective, task.input,
                             task.constraints, task.verification_requirements, task.risk_class, execution_id)
            action = ActionSpec("act:" + child.task_id, "compute", execution_id=child.execution_id, risk_class=child.risk_class)
            decision, result = self.action_gate.authorize_and_execute(
                action,
                lambda: agent.run(child),
                calls_used=len(results),
                execution_id=child.execution_id,
            )
            self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
            if not decision.allowed:
                return {"status": "rejected", "reason": decision.reason, "verification": decision.verification, "task_id": child.task_id}
            if not isinstance(result, AgentResult):
                check = VerificationResult(False, "execution", "malformed_agent_result")
                self.audit.record("agent_result_contract_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            output = result.output
            if not result.is_well_formed():
                check = VerificationResult(False, "agent_result", "malformed_agent_result")
                self.audit.record("agent_result_contract_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.agent_id != agent.agent_id:
                check = VerificationResult(False, "agent_result", "agent_identity_mismatch")
                self.audit.record("agent_identity_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.task_id != child.task_id:
                check = VerificationResult(False, "agent_result", "task_identity_mismatch")
                self.audit.record("task_identity_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.execution_id != execution_id:
                check = VerificationResult(False, "agent_result", "execution_identity_mismatch")
                self.audit.record("execution_identity_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.status != "completed":
                check = VerificationResult(False, "agent_result", "invalid_result_status")
                self.audit.record("result_status_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.verification is None or not result.verification.is_well_formed() or not result.verification.valid:
                check = VerificationResult(False, "agent_result", "unverified_agent_result")
                self.audit.record("result_verification_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if result.verification.stage != "agent_result":
                check = VerificationResult(False, "agent_result", "verification_stage_mismatch")
                self.audit.record("verification_stage_failure", task_id=child.task_id, reason=check.reason)
                return {"status": "rejected", "reason": check.reason, "verification": check, "task_id": child.task_id}
            if deadline_exceeded():
                self.audit.record("task_timeout", task_id=child.task_id, reason="max_task_seconds_exceeded")
                return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": child.task_id}
            if not self.limits.validate_output(output) or not self.limits.validate_output_items(output):
                self.audit.record("output_limit", task_id=child.task_id, allowed=False, reason="output_limit_exceeded")
                return {"status": "rejected", "reason": "output_limit_exceeded", "task_id": child.task_id}
            runtime_verification = self.verifier.verify_output(output, stage="runtime_result")
            self.audit.record("runtime_output_verification", task_id=child.task_id, valid=runtime_verification.valid, reason=runtime_verification.reason)
            if not runtime_verification.valid:
                return {"status": "rejected", "reason": "runtime_output_verification_failed", "verification": runtime_verification, "task_id": child.task_id}
            results.append(result)
            self.audit.record("agent_result", task_id=child.task_id, agent_id=agent.agent_id, status=result.status)

        if deadline_exceeded():
            self.audit.record("task_timeout", task_id=task_id, reason="max_task_seconds_exceeded")
            return {"status": "rejected", "reason": "max_task_seconds_exceeded", "task_id": task_id}

        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.VERIFYING)
        final_verification = self.verifier.verify_output(results[-1].output if results else None, stage="runtime_result")
        if not final_verification.valid:
            self.audit.record("state_commit_rejected", task_id=task_id, reason="final_verification_failed")
            return {"status": "rejected", "reason": "final_verification_failed", "verification": final_verification, "task_id": task_id}
        committed_state = NORYXState(
            input_digest=hashlib.sha256(str(task.input).encode("utf-8")).hexdigest(),
            goal=task.objective,
            subtasks=[x.subtask_id for x in subtasks],
            final_answer=str(results[-1].output) if results else "",
            verification_results=[{"stage": final_verification.stage, "valid": final_verification.valid, "reason": final_verification.reason}],
            confidence=1.0,
            status="verified",
        )
        try:
            commit = self.state.commit(committed_state, execution_id=execution_id, task_id=task_id,
                                       verification_valid=final_verification.valid, verification_stage=final_verification.stage)
        except (TypeError, ValueError, PermissionError, MemoryError) as exc:
            self.audit.record("state_commit_failure", task_id=task_id, reason=type(exc).__name__)
            return {"status": "rejected", "reason": "state_commit_failed", "task_id": task_id}
        envelope, _ = OrchestrationCoordinator.transition(envelope, OrchestrationStage.COMMITTED)
        self.audit.record("orchestration_commit", task_id=task_id, stage=envelope.stage.value,
                          context_id=interaction_context.context_id, execution_id=execution_id,
                          state_sequence=commit.sequence)
        return {"status": "completed", "results": tuple(results), "state_commit": commit,
                "orchestration_stage": envelope.stage.value, "audit": self.audit.snapshot()}

    def run_hypersynth(self, task: TaskSpec, interaction_context: InteractionContext | None = None):
        """Execute a task through the bounded HYPERSYNTH cognitive pipeline."""
        if interaction_context is None or not isinstance(interaction_context, InteractionContext):
            return {"status": "rejected", "reason": "interaction_context_required", "task_id": getattr(task, "task_id", None)}
        return self.hypersynth.run(task, interaction_context=interaction_context)
