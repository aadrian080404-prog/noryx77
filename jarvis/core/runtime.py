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
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.engine import RuntimeEngine

class JarvisRuntime:
    """Bounded JARVIS runtime: propose -> authorize -> reserve -> execute -> verify -> commit -> audit."""
    def __init__(self, *, orchestrator=None, registry=None, audit=None, state_store=None, recovery=None, system_fabric=None):
        self.orchestrator = orchestrator or JarvisOrchestrator(policy=Policy()); self.audit = audit or AuditLog(); self.state = state_store or JarvisStateStore(); self.recovery = recovery or RecoveryController()
        self.core_verifier = VerificationEngine(); self.core_policy = PolicyEngine(); self.core_security = SecurityBoundary(self.core_policy, self.core_verifier)
        self.system_fabric = system_fabric or CanonicalSystemFabric()
        if not isinstance(self.system_fabric, CanonicalSystemFabric): raise TypeError("system_fabric_invalid")
        self.identity_registry = IdentityRegistry(); self.jarvis_identity, self._jarvis_private_key = AgentIdentityAuthority.generate("jarvis"); self.identity_registry.register(self.jarvis_identity)
        self.authorization = AuthorizationAuthority(secrets.token_bytes(32), identity_registry=self.identity_registry)
        self.core_action_gate = ActionGate(self.core_policy, self.core_security, RuntimeLimits(), authorization=self.authorization)
        self.tool_executor = ToolExecutor(self.core_action_gate, self.core_verifier)
        if registry is not None: raise TypeError("external_registry_must_be_canonical_core_registry")
        self.registry = CapabilityRegistry(core_registry=self.tool_executor.capabilities)
        self.runtime_engine = RuntimeEngine()
        self.runtime_bridge = JarvisRuntimeBridge(runtime_engine=self.runtime_engine, tool_executor=self.tool_executor, verifier=self.core_verifier, authorization=self.authorization, principal=self.jarvis_identity, policy=self.orchestrator.policy, system_fabric=self.system_fabric)
        if not isinstance(self.recovery, RecoveryController): raise TypeError("invalid_recovery_controller")
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
        if not isinstance(request, Request) or not isinstance(plan, Plan): raise TypeError("request and plan types are required")
        if plan.request_id != request.request_id: raise PermissionError("request_identity_mismatch")
        recovery_state, recovery_epoch = self.recovery.snapshot()
        if recovery_state is not RecoveryState.NORMAL:
            self.audit.record("recovery_execution_denied", request.principal_id); return ()
        if not plan.steps:
            self.audit.record("execution_authorization_rejected", request.principal_id); raise PermissionError("capability_denied")
        for step in plan.steps:
            if not self.orchestrator.policy.authorize(request.principal_id, step.capability, step.target):
                self.audit.record("execution_authorization_rejected", request.principal_id, reason="capability_denied"); raise PermissionError("capability_denied")
        execution_id = request.request_id
        runtime_id = self.runtime_engine.runtime_id
        try:
            self.state.reserve(execution_id=execution_id, request_id=request.request_id, principal_id=request.principal_id)
        except (PermissionError, ValueError) as exc:
            self.audit.record("execution_reservation_rejected", request.principal_id, reason=str(exc)); return ()
        self.audit.record("execution_started", request.principal_id)
        try:
            results = self.recovery.run_if_normal(lambda: self.runtime_bridge.execute(request, plan), expected_epoch=recovery_epoch)
        except PermissionError as exc:
            self.audit.record("execution_authorization_rejected", request.principal_id, reason=str(exc))
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": str(exc), "stage": "bridge"}, runtime_id=runtime_id)
            return ()
        except Exception as exc:
            self.audit.record("execution_failed", request.principal_id, reason=str(exc))
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": type(exc).__name__, "stage": "bridge"}, runtime_id=runtime_id)
            return ()
        if not isinstance(results, tuple):
            self.audit.record("execution_failed", request.principal_id, reason="invalid_bridge_result")
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": "invalid_bridge_result", "stage": "verification"}, runtime_id=runtime_id)
            return ()
        if not self._verify_results(plan, results):
            self.audit.record("execution_verification_failed", request.principal_id)
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": "result_verification_failed", "stage": "verification"}, runtime_id=runtime_id)
            return ()
        state = JarvisState(execution_id=execution_id, request_id=request.request_id, principal_id=request.principal_id, request_digest=self.state.digest_request(request.text), results=list(results))
        try:
            self.recovery.run_if_normal(lambda: self.state.commit(execution_id=execution_id, state=state), expected_epoch=recovery_epoch)
        except (PermissionError, ValueError) as exc:
            self.audit.record("state_commit_rejected", request.principal_id, reason=str(exc))
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": str(exc), "stage": "state_commit"}, runtime_id=runtime_id)
            return ()
        committed = self.state.get(execution_id, principal_id=request.principal_id)
        if committed is None:
            self.audit.record("state_commit_rejected", request.principal_id, reason="committed_state_missing")
            self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_rejected", metadata={"reason": "committed_state_missing", "stage": "state_commit"}, runtime_id=runtime_id)
            return ()
        self.system_fabric.record_execution(execution_id=execution_id, client_id=request.principal_id, phase="jarvis_committed", metadata={"status": "committed", "result_count": len(results), "state_sequence": committed.sequence}, runtime_id=runtime_id)
        self.audit.record("state_committed", request.principal_id); self.audit.record("execution_finished", request.principal_id)
        return results
