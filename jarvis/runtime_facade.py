from __future__ import annotations
from dataclasses import dataclass
from jarvis.agent.front_end import AgentInput, JarvisInteractionFrontEnd
from jarvis.core.runtime import JarvisRuntime
from jarvis.core.contracts import Request, Plan

@dataclass(frozen=True)
class InteractionResult:
    accepted: bool
    reason: str
    results: tuple

class JarvisFacade:
    """Single user-facing facade; perception never bypasses JarvisRuntime."""
    def __init__(self, runtime: JarvisRuntime|None=None, frontend: JarvisInteractionFrontEnd|None=None):
        self.runtime=runtime or JarvisRuntime(); self.frontend=frontend or JarvisInteractionFrontEnd()
    def accept_input(self, item: AgentInput, plan: Plan) -> InteractionResult:
        request=Request(request_id=plan.request_id, principal_id="user", text=item.text)
        try: results=self.runtime.execute(request,plan); return InteractionResult(bool(results),"executed" if results else "execution_rejected",results)
        except (PermissionError,ValueError,TypeError) as exc: return InteractionResult(False,type(exc).__name__,())
