from .contracts import Request, Plan, ActionResult
from .policy import Policy

class JarvisOrchestrator:
    def __init__(self, policy=None):
        self.policy = policy or Policy()

    def authorize_step(self, request: Request, step) -> bool:
        return self.policy.authorize(request.principal_id, step.capability, step.target)

    def execute(self, request: Request, plan: Plan, executor):
        if plan.request_id != request.request_id:
            raise ValueError("request_plan_mismatch")
        seen = set()
        results = []
        completed = set()
        for step in plan.steps:
            if step.step_id in seen:
                raise ValueError("duplicate_step_id")
            seen.add(step.step_id)
            if step.dependencies and not set(step.dependencies).issubset(completed):
                raise ValueError("unsatisfied_dependencies")
            if not self.authorize_step(request, step):
                raise PermissionError("capability_denied")
            try:
                result = executor(step)
            except Exception as exc:
                results.append(ActionResult(step.step_id, False, error=type(exc).__name__))
                break
            if not isinstance(result, ActionResult):
                raise TypeError("executor must return ActionResult")
            if result.step_id != step.step_id:
                raise ValueError("result_step_mismatch")
            results.append(result)
            if not result.success:
                break
            completed.add(step.step_id)
        return tuple(results)
