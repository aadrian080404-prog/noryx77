from .contracts import Request, Plan, ActionResult
from .orchestrator import JarvisOrchestrator
from jarvis.security.audit import AuditLog
from jarvis.tools.registry import CapabilityRegistry

class JarvisRuntime:
    """Bounded JARVIS runtime: propose -> authorize -> execute -> audit."""
    def __init__(self, *, orchestrator=None, registry=None, audit=None):
        self.orchestrator = orchestrator or JarvisOrchestrator()
        self.registry = registry or CapabilityRegistry()
        self.audit = audit or AuditLog()

    def execute(self, request: Request, plan: Plan):
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
