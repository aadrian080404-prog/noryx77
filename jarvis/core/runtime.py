from .contracts import Request, Plan, ActionResult
from .orchestrator import JarvisOrchestrator
from .policy import Policy
from .recovery import RecoveryController, RecoveryState
from .state import JarvisState, JarvisStateStore
from jarvis.security.audit import AuditLog
from jarvis.tools.registry import CapabilityRegistry

class JarvisRuntime:
    """Bounded JARVIS runtime: propose -> authorize -> reserve -> execute -> verify -> commit -> audit."""
    def __init__(self, *, orchestrator=None, registry=None, audit=None, state_store=None, recovery=None):
        self.orchestrator = orchestrator or JarvisOrchestrator(policy=Policy()); self.registry = registry or CapabilityRegistry(); self.audit = audit or AuditLog(); self.state = state_store or JarvisStateStore(); self.recovery = recovery or RecoveryController()
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
        if not plan.steps or not self.orchestrator.authorize_step(request, plan.steps[0]):
            self.audit.record("execution_authorization_rejected", request.principal_id); raise PermissionError("capability_denied")
        execution_id = request.request_id
        try:
            self.state.reserve(execution_id=execution_id, request_id=request.request_id, principal_id=request.principal_id)
        except (PermissionError, ValueError) as exc:
            self.audit.record("execution_reservation_rejected", request.principal_id, reason=str(exc)); return ()
        def executor(step):
            handler = self.registry.resolve(step.capability)
            if handler is None: raise LookupError("capability_not_found")
            result = handler(step)
            if not isinstance(result, ActionResult): raise TypeError("capability must return ActionResult")
            self.audit.record("action_completed" if result.success else "action_failed", request.principal_id); return result
        self.audit.record("execution_started", request.principal_id)
        try:
            results = self.recovery.run_if_normal(lambda: self.orchestrator.execute(request, plan, executor), expected_epoch=recovery_epoch)
        except PermissionError as exc:
            self.audit.record("recovery_execution_denied", request.principal_id, reason=str(exc)); return ()
        except Exception:
            self.audit.record("execution_failed", request.principal_id, reason="controlled_runtime_failure"); return ()
        if not self._verify_results(plan, results):
            self.audit.record("state_commit_rejected", request.principal_id, reason="result_verification_failed"); return results
        state = JarvisState(execution_id=execution_id, request_id=request.request_id, principal_id=request.principal_id, request_digest=self.state.digest_request(request.text), completed_steps=[result.step_id for result in results], results=[{"step_id": result.step_id, "success": result.success, "output": result.output} for result in results], status="verified")
        try:
            self.recovery.run_if_normal(lambda: self.state.commit(state, verified_results=True, execution_id=execution_id, request_id=request.request_id, principal_id=request.principal_id), expected_epoch=recovery_epoch)
        except (TypeError, ValueError, PermissionError, MemoryError):
            self.audit.record("state_commit_rejected", request.principal_id, reason="recovery_or_state_failure"); return results
        self.audit.record("state_committed", request.principal_id); self.audit.record("execution_finished", request.principal_id); return results
