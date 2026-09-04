from .contracts import Request, Plan, ActionResult
from .policy import Policy

class JarvisOrchestrator:
    def __init__(self, policy=None):
        self.policy = policy or Policy()

    def authorize_step(self, request: Request, step) -> bool:
        return self.policy.authorize(request.principal_id, step.capability, step.target)

    def execute(self, request: Request, plan: Plan, executor):
        results = []
        completed = set()
        for step in plan.steps:
            if step.dependencies and not set(step.dependencies).issubset(completed):
                raise ValueError("unsatisfied_dependencies")
            if not self.authorize_step(request, step):
                raise PermissionError("capability_denied")
            result = executor(step)
            if not isinstance(result, ActionResult):
                raise TypeError("executor must return ActionResult")
            results.append(result)
            if not result.success:
                break
            completed.add(step.step_id)
        return tuple(results)
