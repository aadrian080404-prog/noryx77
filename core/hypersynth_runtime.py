import hashlib
import inspect
import time

from .actions import ActionGate
from .audit import AuditLog
from .collaboration import AgentCollaboration
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .interaction_context import InteractionContext
from .limits import RuntimeLimits
from .memory import MemoryStore
from .policy import PolicyEngine
from .recovery import RecoveryController, RecoveryState
from .router import ResourceRouter
from .security import SecurityBoundary
from .verification import VerificationEngine
from .tools import ToolExecutor
from .frontier_capabilities import install_frontier_capabilities
from .universal_intelligence import UniversalIntelligenceFabric
from noryx7_runtime.engine import RuntimeEngine


class HypersynthRuntime:
    """Fail-closed facade owning HYPERSYNTH safety dependencies and context."""
    def __init__(self, verifier=None, router=None, planner=None, audit=None, limits=None, memory=None, clock=None, recovery=None, universal_intelligence=None, runtime_engine=None):
        self.audit = audit or AuditLog()
        if runtime_engine is not None and not isinstance(runtime_engine, RuntimeEngine): raise TypeError("invalid_runtime_engine")
        self.runtime_engine = runtime_engine
        self.verifier = verifier or VerificationEngine()
        self.router = router or ResourceRouter()
        self.limits = limits or RuntimeLimits()
        self.clock = clock or time.monotonic
        self.policy = PolicyEngine()
        self.recovery = recovery or RecoveryController()
        if not isinstance(self.recovery, RecoveryController): raise TypeError("invalid_recovery_controller")
        self.identity_registry = getattr(self.router, "identity_registry", None)
        self.security = SecurityBoundary(self.policy, self.verifier, self.recovery)
        self.action_gate = ActionGate(self.policy, self.security, self.limits)
        self.tool_executor = ToolExecutor(self.action_gate, self.verifier, runtime_engine=runtime_engine)
        self.frontier_capabilities = install_frontier_capabilities(self.tool_executor)
        self.collaboration = AgentCollaboration(self.verifier)
        self.tool_executor.capabilities.register("agent_collaboration", self._execute_agent_collaboration, risk_class="normal")
        self.memory = memory or MemoryStore(max_items=self.limits.max_memory_items)
        self.universal_intelligence = universal_intelligence or UniversalIntelligenceFabric()
        if not isinstance(self.universal_intelligence, UniversalIntelligenceFabric): raise TypeError("invalid_universal_intelligence_fabric")
        self.kernel = Hypersynth(
            self.verifier, self.router, planner=planner, action_gate=self.action_gate,
            memory=self.memory, audit=self.audit, max_steps=self.limits.max_actions_per_task,
            recovery=self.recovery, tool_executor=self.tool_executor,
            universal_intelligence=self.universal_intelligence,
        )

    def _execute_agent_collaboration(self, target, parameters):
        """Run Primary -> Secondary -> Primary inside the canonical tool boundary."""
        if not isinstance(target, str) or not target.strip(): raise ValueError("collaboration_target_required")
        if not isinstance(parameters, dict): raise TypeError("collaboration_parameters_required")
        task_id = parameters.get("task_id")
        task_type = parameters.get("task_type", "compute")
        execution_id = parameters.get("execution_id")
        task_input = parameters.get("input")
        constraints = parameters.get("constraints", {})
        verification_requirements = parameters.get("verification_requirements", ())
        risk_class = parameters.get("risk_class", "normal")
        if not all(isinstance(value, str) and value.strip() for value in (task_id, task_type, execution_id)): raise ValueError("collaboration_task_identity_required")
        if not isinstance(constraints, dict) or not isinstance(verification_requirements, (tuple, list)): raise ValueError("invalid_collaboration_task_contract")
        task = TaskSpec(task_id, task_type, target, task_input, constraints, tuple(verification_requirements), risk_class, execution_id)
        primary = self.router.get("noryx7-llm")
        secondary = self.router.get("noryx7-secondary")
        if primary is None or secondary is None: raise RuntimeError("primary_secondary_unavailable")
        reconciliation, check = self.collaboration.run(task, primary, secondary)
        if not isinstance(check, VerificationResult) or not check.is_well_formed() or not check.valid: raise RuntimeError("collaboration_not_verified")
        self.audit.record("agent_collaboration_completed", task_id=task_id, execution_id=execution_id, primary_agent=primary.agent_id, secondary_agent=secondary.agent_id, output_digest=reconciliation.proposal_digest)
        return reconciliation.output

    def _principal_binding(self, agent_ids):
        """Bind registered identities when a registry is installed; standalone routers have no commit authority."""
        bindings = []
        registry = getattr(self.router, "identity_registry", None)
        for agent_id in tuple(agent_ids):
            agent = self.router.route(agent_id)
            identity = getattr(agent, "identity", None)
            if registry is None:
                bindings.append((agent_id, None))
                continue
            if not registry.is_trusted(identity): raise PermissionError("agent_identity_untrusted")
            bindings.append((identity.agent_id, hashlib.sha256(identity.public_key).hexdigest()))
        return tuple(bindings)

    @staticmethod
    def _default_interaction_context(task):
        """Create a bounded empty context only for the legacy direct runtime API."""
        context_id = hashlib.sha256(f"runtime:{getattr(task, 'task_id', '')}".encode("utf-8")).hexdigest()
        return InteractionContext(profile_id="runtime", signals=(), context_id=context_id)

    def run(self, task: TaskSpec, *, interaction_context: InteractionContext | None = None, preferred_agent=None):
        task_id = getattr(task, "task_id", None)
        started = self.clock()
        deadline = started + self.limits.max_task_seconds
        recovery_state, recovery_epoch = self.recovery.snapshot()
        self.audit.record("hypersynth_start", task_id=task_id, context_id=getattr(interaction_context, "context_id", None))

        def deadline_exceeded(): return self.clock() > deadline

        if recovery_state is not RecoveryState.NORMAL:
            check = VerificationResult(False, "recovery", "recovery_state_denies_execution")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="recovery", reason=check.reason)
            return {"status":"rejected","phase":"recovery","verification":check,"audit":self.audit.snapshot()}
        if interaction_context is None: interaction_context = self._default_interaction_context(task)
        if not isinstance(interaction_context, InteractionContext):
            check = VerificationResult(False, "context", "interaction_context_required")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="context", reason=check.reason)
            return {"status":"rejected","phase":"context","verification":check,"audit":self.audit.snapshot()}
        try: interaction_context.as_prompt_context()
        except (TypeError, ValueError):
            check = VerificationResult(False, "context", "invalid_interaction_context")
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="context", reason=check.reason)
            return {"status":"rejected","phase":"context","verification":check,"audit":self.audit.snapshot()}
        try:
            self.recovery.require_normal(expected_epoch=recovery_epoch)
            task_check = self.verifier.verify_task(task)
            if not isinstance(task_check, VerificationResult) or not task_check.is_well_formed():
                check = VerificationResult(False, "contract", "invalid_task_verification")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status":"rejected","phase":"perception","verification":check,"execution_id":getattr(task,"execution_id",None),"audit":self.audit.snapshot()}
            if not task_check.valid:
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=task_check.reason)
                return {"status":"rejected","phase":"perception","verification":task_check,"execution_id":getattr(task,"execution_id",None),"audit":self.audit.snapshot()}
            if deadline_exceeded():
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status":"rejected","phase":"perception","verification":check,"execution_id":getattr(task,"execution_id",None),"audit":self.audit.snapshot()}
            if not self.limits.validate_input(task.input):
                check = VerificationResult(False, "limits", "input_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status":"rejected","phase":"perception","verification":check,"execution_id":getattr(task,"execution_id",None),"audit":self.audit.snapshot()}
            if not self.limits.validate_input(task.objective):
                check = VerificationResult(False, "limits", "objective_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="perception", reason=check.reason)
                return {"status":"rejected","phase":"perception","verification":check,"execution_id":getattr(task,"execution_id",None),"audit":self.audit.snapshot()}
            self.audit.record("hypersynth_context_bound", task_id=task_id, context_id=interaction_context.context_id)
            available = self.router.available()
            principal_bindings = self._principal_binding(available) if available else ()
            if available: self.audit.record("hypersynth_identity_bound", task_id=task_id, principals=tuple(x[0] for x in principal_bindings), fingerprints=tuple(x[1] for x in principal_bindings))
            kernel_parameters = inspect.signature(self.kernel.run).parameters
            kernel_accepts_context = "interaction_context" in kernel_parameters or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in kernel_parameters.values())
            if kernel_accepts_context:
                result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent, interaction_context=interaction_context) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded, interaction_context=interaction_context)
            else:
                result = self.kernel.run(task, deadline_check=deadline_exceeded, preferred_agent=preferred_agent) if preferred_agent is not None else self.kernel.run(task, deadline_check=deadline_exceeded)
            if not isinstance(result, dict):
                check = VerificationResult(False, "runtime", "malformed_kernel_result")
                self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                return {"status":"rejected","phase":"execution","verification":check,"audit":self.audit.snapshot()}
            kernel_check = result.get("verification")
            kernel_results = result.get("results", ())
            if result.get("status") == "rejected" and isinstance(kernel_check, VerificationResult) and kernel_check.reason == "output_limit_exceeded" and isinstance(kernel_results, (tuple, list)) and kernel_results:
                final_kernel_result = kernel_results[-1]
                structured_output = getattr(final_kernel_result, "output", None)
                if not self.limits.validate_output_items(structured_output):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    result["verification"] = check
                    result["audit"] = self.audit.snapshot()
                    return result
            if deadline_exceeded() and result.get("status") == "completed":
                check = VerificationResult(False, "limits", "task_time_limit_exceeded")
                self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
            self.recovery.require_normal(expected_epoch=recovery_epoch)
            if result.get("status") == "completed":
                result_check = result.get("verification")
                if (not isinstance(result_check, VerificationResult) or not result_check.is_well_formed() or not result_check.valid or result_check.stage != "hypersynth_result"):
                    check = VerificationResult(False, "runtime", "invalid_kernel_verification")
                    self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                    return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
                output = result.get("results", ())
                if not isinstance(output, tuple):
                    check = VerificationResult(False, "runtime", "malformed_kernel_results")
                    self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
                    return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
                if not self.limits.validate_count(len(output), self.limits.max_output_items):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
                final_output = output[-1].output if output else None
                if not self.limits.validate_output_items(final_output):
                    check = VerificationResult(False, "limits", "output_item_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
                if not self.limits.validate_output(final_output):
                    check = VerificationResult(False, "limits", "output_limit_exceeded")
                    self.audit.record("hypersynth_rejected", task_id=task_id, phase="verification", reason=check.reason)
                    return {"status":"rejected","phase":"verification","verification":check,"audit":self.audit.snapshot()}
        except PermissionError as exc:
            check = VerificationResult(False, "identity", str(exc))
            self.audit.record("hypersynth_rejected", task_id=task_id, phase="identity", reason=check.reason)
            return {"status":"rejected","phase":"identity","verification":check,"audit":self.audit.snapshot()}
        except Exception:
            check = VerificationResult(False, "runtime", "controlled_runtime_failure")
            self.audit.record("hypersynth_failure", task_id=task_id, reason=check.reason)
            return {"status":"rejected","phase":"execution","reason":check.reason,"verification":check,"audit":self.audit.snapshot()}
        result["audit"] = self.audit.snapshot()
        return result
