from .contracts import Request, Plan, ActionResult
from .orchestrator import JarvisOrchestrator
from .policy import Policy
from jarvis.security.audit import AuditLog
from jarvis.tools.registry import CapabilityRegistry

class JarvisRuntime:
    """Bounded JARVIS runtime: propose -> authorize -> execute -> audit."""
    def __init__(self, *, orchestrator=None, registry=None, audit=None):
        self.orchestrator = orchestrator or JarvisOrchestrator(policy=Policy())
        self.registry = registry or CapabilityRegistry()
        self.audit = audit or AuditLog()

    def grant(self, principal_id: str, capability: str, target: str) -> None:
        if not isinstance(self.orchestrator.policy, Policy):
            raise TypeError("runtime policy does not support grants")
        self.orchestrator.policy.grant(principal_id, capability, target)

    def revoke(self, principal_id: str, capability: str, target: str) -> None:
        if not isinstance(self.orchestrator.policy, Policy):
            raise TypeError("runtime policy does not support revocation")
        self.orchestrator.policy.revoke(principal_id, capability, target)

    def execute(self, request: Request, plan: Plan):
        if not isinstance(request, Request) or not isinstance(plan, Plan):
            raise TypeError("request and plan types are required")
        if plan.request_id != request.request_id:
            raise PermissionError("request_identity_mismatch")

        def executor(step):
            handler = self.registry.resolve(step.capability)
            if handler is None:
                raise LookupError("capability_not_found")
            result = handler(step)
            if not isinstance(result, ActionResult):
                raise TypeError("capability must return ActionResult")
            self.audit.record("action_completed" if result.success else "action_failed", request.principal_id)
            return result

        self.audit.record("execution_started", request.principal_id)
        results = self.orchestrator.execute(request, plan, executor)
        self.audit.record("execution_finished", request.principal_id)
        return results
