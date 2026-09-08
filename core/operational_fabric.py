from __future__ import annotations

from .contracts import AgentResult, TaskSpec, VerificationResult
from .supervisor import AgentDecision, AgentSupervisor


class OperationalAgentFabric:
    """Canonical operational fabric: registry/trust -> supervisor -> router -> live agent.

    HYPERSYNTH uses this object as its supervisor so allocation and execution share
    one concrete dispatch path. It never grants authority and never bypasses
    ActionGate, policy, security or verification.
    """

    def __init__(self, router, verifier, audit=None):
        self.router = router
        self.verifier = verifier
        self.audit = audit
        self.supervisor = AgentSupervisor(router, verifier, audit=audit)

    def available(self) -> tuple[str, ...]:
        return tuple(self.router.available())

    def online(self) -> tuple[str, ...]:
        result = []
        for agent_id in self.available():
            try:
                agent = self.router.get(agent_id)
                identity = getattr(agent, "identity", None)
                trusted = self.router.identity_is_trusted(identity) if identity is not None else False
                if trusted:
                    result.append(agent_id)
            except Exception:
                continue
        return tuple(result)

    def select(self, task: TaskSpec, preferred=None):
        selected, decision = self.supervisor.select(task, preferred=preferred)
        if self.audit and decision.accepted:
            self.audit.record(
                "operational_fabric_dispatch_selected",
                task_id=task.task_id,
                execution_id=task.execution_id,
                agent_id=decision.agent_id,
            )
        return selected, decision

    def admit(self, task: TaskSpec, result: AgentResult, *, selected_agent_id: str | None = None) -> VerificationResult:
        check = self.supervisor.admit(task, result, selected_agent_id=selected_agent_id)
        if self.audit:
            self.audit.record(
                "operational_fabric_result_admitted" if check.valid else "operational_fabric_result_rejected",
                task_id=getattr(task, "task_id", None),
                execution_id=getattr(task, "execution_id", ""),
                agent_id=getattr(result, "agent_id", None),
                reason=check.reason,
            )
        return check

    def dispatch(self, task: TaskSpec, preferred=None):
        """Dispatch one bounded task through the canonical fabric and admit its result."""
        selected, decision = self.select(task, preferred=preferred)
        if not decision.accepted or selected is None:
            return None, VerificationResult(False, "allocation", decision.reason)
        try:
            result = selected.run(task)
        except Exception:
            return None, VerificationResult(False, "execution", "agent_execution_failure")
        admission = self.admit(task, result, selected_agent_id=selected.agent_id)
        return result, admission

    def status(self) -> dict[str, object]:
        return {
            "available": self.available(),
            "online": self.online(),
            "count": len(self.available()),
        }
