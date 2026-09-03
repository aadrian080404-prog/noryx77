from .agents import Agent


class ResourceRouter:
    """Selects registered agents without coupling orchestration to implementations."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        agent_id = getattr(agent, "agent_id", None)
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("agent_id required")
        if agent_id in self._agents:
            raise ValueError("agent_id already registered")
        self._agents[agent_id] = agent

    def get(self, agent_id: str):
        return self._agents.get(agent_id)

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))

    def default_id(self) -> str:
        """Return the sole deterministic route; fail closed when routing is ambiguous."""
        if len(self._agents) != 1:
            raise LookupError("no unique default resource route")
        return next(iter(self._agents))

    def route(self, preferred: str | None = None):
        if preferred:
            agent = self._agents.get(preferred)
            if agent is None:
                raise LookupError("requested agent unavailable")
            return agent
        if len(self._agents) == 1:
            return next(iter(self._agents.values()))
        raise LookupError("no unambiguous resource route")
