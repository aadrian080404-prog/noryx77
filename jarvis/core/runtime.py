import secrets
from .contracts import Request, Plan, ActionResult
from .orchestrator import JarvisOrchestrator
from .policy import Policy
from .recovery import RecoveryController, RecoveryState
from .state import JarvisState, JarvisStateStore
from jarvis.security.audit import AuditLog
from jarvis.tools.registry import CapabilityRegistry
from core.jarvis_runtime_bridge import JarvisRuntimeBridge
from core.verification import VerificationEngine
from core.policy import PolicyEngine
from core.security import SecurityBoundary
from core.limits import RuntimeLimits
from core.actions import ActionGate, AuthorizationAuthority
from core.tools import ToolExecutor
from core.identity import AgentIdentityAuthority, IdentityRegistry
from noryx7_runtime.engine import RuntimeEngine
from core.system_fabric import CanonicalSystemFabric
from core.execution_trace import ExecutionTrace
from core.provider_router import Provider
from core.provider_execution import ProviderExecutionGateway
from core.provider_resilience import ResilientProviderExecutor

class JarvisRuntime:
    """Bounded JARVIS runtime: propose -> authorize -> reserve -> execute -> verify -> commit -> audit."""
    def __init__(self, *, orchestrator=None, registry=None, audit=None, state_store=None, recovery=None):
        self.orchestrator = orchestrator or JarvisOrchestrator(policy=Policy()); self.audit = audit or AuditLog(); self.state = state_store or JarvisStateStore(); self.recovery = recovery or RecoveryController()

        # Canonical NORYX7 execution infrastructure.
        self.core_verifier = VerificationEngine()
        self.core_policy = PolicyEngine()
        self.core_security = SecurityBoundary(
            self.core_policy,
            self.core_verifier,
        )

        # Canonical JARVIS execution identity and authorization authority.
        # JARVIS is an agent identity; request.principal_id remains the
        # user-level principal handled by the legacy JARVIS Policy.
        self.identity_registry = IdentityRegistry()
        self.jarvis_identity, self._jarvis_private_key = (
            AgentIdentityAuthority.generate("jarvis")
        )
        self.identity_registry.register(self.jarvis_identity)
        self.authorization = AuthorizationAuthority(
            secrets.token_bytes(32),
            identity_registry=self.identity_registry,
        )

        self.core_action_gate = ActionGate(
            self.core_policy,
            self.core_security,
            RuntimeLimits(),
            authorization=self.authorization,
        )
        self.tool_executor = ToolExecutor(
            self.core_action_gate,
            self.core_verifier,
        )

        # JARVIS and the canonical ToolExecutor now share ONE capability registry.
        # No duplicated execution registry is kept.
        if registry is not None:
            raise TypeError("external_registry_must_be_canonical_core_registry")

        self.registry = CapabilityRegistry(
            core_registry=self.tool_executor.capabilities,
        )
        self.provider_execution = ProviderExecutionGateway()
        self.provider_resilience = ResilientProviderExecutor()
        self.registry.register("provider_execute", self._execute_provider_capability)
        self.runtime_engine = RuntimeEngine()
        self.execution_traces: dict[str, ExecutionTrace] = {}
        self.system_fabric = CanonicalSystemFabric(
            runtime_engine=self.runtime_engine,
            tool_executor=self.tool_executor,
            verifier=self.core_verifier,
            authorization=self.authorization,
            principal=self.jarvis_identity,
            policy=self.orchestrator.policy,
        )
        self.runtime_bridge = JarvisRuntimeBridge(
            runtime_engine=self.runtime_engine,
            tool_executor=self.tool_executor,
            verifier=self.core_verifier,
            authorization=self.authorization,
            principal=self.jarvis_identity,
            policy=self.orchestrator.policy,
            system_fabric=self.system_fabric,
        )
        if not isinstance(self.recovery, RecoveryController): raise TypeError("invalid_recovery_controller")
    def _trace_for(self, execution_id: str) -> ExecutionTrace:
        trace = self.execution_traces.get(execution_id)
        if trace is None:
            if len(self.execution_traces) >= 10_000:
                oldest = next(iter(self.execution_traces))
                self.execution_traces.pop(oldest, None)
            trace = ExecutionTrace(execution_id)
            self.execution_traces[execution_id] = trace
        return trace

    def register_provider(self, provider: Provider) -> None:
        self.provider_execution.register(provider)
        self.provider_resilience.register(provider)

    def _execute_provider_capability(self, step):
        capability = step.parameters.get("provider_capability")
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("provider_capability_required")
        principal_id = step.parameters.get("__jarvis_principal_id")
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise PermissionError("provider_principal_required")
        payload = step.parameters.get("payload")
        result = self.provider_execution.execute(
            capability,
            payload,
            principal_id=principal_id,
            logical_target=step.target,
            authorize_capability="provider_execute",
            authorize=self.orchestrator.policy.authorize,
        )
        return {
            "provider": result.provider,
            "capability": result.capability,
            "output": result.output,
        }

    def grant(self, principal_id: str, capability: str, target: str) -> None:
        if not isinstance(self.orchestrator.policy, Policy): raise TypeError("runtime policy does not support grants")
        self.orchestrator.policy.grant(principal_id, capability, target)
    def revoke(self, principal_id: str, capability: str, target: str) -> None:
        if not isinstance(self.orchestrator.policy, Policy): raise TypeError("runtime policy does not support revocation")
        self.orchestrator.policy.revoke(principal_id, capability, target)
    @staticmethod
    def _verify_results(plan: Plan, results: tuple[ActionResult, ...]) -> bool:
        if len(results) != len(plan.steps): return False
        expected = tuple(step.step_id for step in plan.steps); actual = tuple(result.step_id for result in results)
        return actual == expected and all(result.success is True for result in results)
    def execute(self, request: Request, plan: Plan):
        if not isinstance(request, Request) or not isinstance(plan, Plan):
            raise TypeError("request and plan types are required")

        if plan.request_id != request.request_id:
            raise PermissionError("request_identity_mismatch")

        trace = self._trace_for(request.request_id)
        trace.append("execution_requested", {"principal_id": request.principal_id})
        recovery_state, recovery_epoch = self.recovery.snapshot()
        if recovery_state is not RecoveryState.NORMAL:
            self.audit.record("recovery_execution_denied", request.principal_id)
            trace.append("execution_denied", {"reason": "recovery"})
            return ()

        if not plan.steps:
            self.audit.record(
                "execution_authorization_rejected",
                request.principal_id,
            )
            trace.append("execution_denied", {"reason": "empty_plan"})
            raise PermissionError("capability_denied")

        # JARVIS user-level authorization is checked before reserving the
        # execution identity. An unauthorized request must not consume a
        # reservation and must preserve the historical PermissionError
        # contract. Canonical cryptographic authorization is still enforced
        # later by ActionGate/AuthorizationAuthority.
        for step in plan.steps:
            if not self.orchestrator.policy.authorize(
                request.principal_id,
                step.capability,
                step.target,
            ):
                self.audit.record(
                    "execution_authorization_rejected",
                    request.principal_id,
                    reason="capability_denied",
                )
                trace.append("execution_denied", {"reason": "capability_denied", "step_id": step.step_id})
                raise PermissionError("capability_denied")

        execution_id = request.request_id

        try:
            self.state.reserve(
                execution_id=execution_id,
                request_id=request.request_id,
                principal_id=request.principal_id,
            )
        except (PermissionError, ValueError) as exc:
            self.audit.record(
                "execution_reservation_rejected",
                request.principal_id,
                reason=str(exc),
            )
            return ()

        self.audit.record("execution_started", request.principal_id)
        trace.append("execution_started", {"principal_id": request.principal_id, "step_count": len(plan.steps)})

        try:
            results = self.recovery.run_if_normal(
                lambda: self.runtime_bridge.execute(request, plan),
                expected_epoch=recovery_epoch,
            )
        except PermissionError as exc:
            self.audit.record(
                "execution_authorization_rejected",
                request.principal_id,
                reason=str(exc),
            )
            return ()
        except Exception as exc:
            self.audit.record(
                "execution_failed",
                request.principal_id,
                reason=str(exc),
            )
            return ()

        trace.append("execution_bridge_completed", {"result_count": len(results) if isinstance(results, tuple) else -1})

        if not isinstance(results, tuple):
            self.audit.record(
                "execution_failed",
                request.principal_id,
                reason="invalid_bridge_result",
            )
            return ()

        if not self._verify_results(plan, results):
            self.audit.record(
                "execution_verification_failed",
                request.principal_id,
            )
            trace.append("execution_verification_failed", {"result_count": len(results)})
            return ()

        state = JarvisState(
            execution_id=execution_id,
            request_id=request.request_id,
            principal_id=request.principal_id,
            request_digest=self.state.digest_request(request.text),
            results=list(results),
        )

        try:
            self.recovery.run_if_normal(
                lambda: self.state.commit(
                    execution_id=execution_id,
                    state=state,
                ),
                expected_epoch=recovery_epoch,
            )
        except (PermissionError, ValueError):
            self.audit.record(
                "state_commit_rejected",
                request.principal_id,
            )
            return ()

        trace.append("state_committed", {"result_count": len(results)})
        self.audit.record("state_committed", request.principal_id)
        self.audit.record("execution_finished", request.principal_id)
        trace.append("execution_finished", {"result_count": len(results)})
        return results
