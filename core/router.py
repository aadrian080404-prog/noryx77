from .agents import Agent


class ResourceRouter:
    """Selects registered agents without coupling orchestration to implementations."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    @staticmethod
    def _validate_agent(agent: Agent) -> str:
        agent_id = getattr(agent, "agent_id", None)
        run = getattr(agent, "run", None)
        if not isinstance(agent_id, str) or not agent_id.strip() or not callable(run):
            raise TypeError("invalid_agent")
        return agent_id

    def register(self, agent: Agent) -> None:
        agent_id = self._validate_agent(agent)
        if agent_id in self._agents:
            raise ValueError("duplicate_agent_id")
        self._agents[agent_id] = agent

    def get(self, agent_id: str):
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        agent = self._agents.get(agent_id)
        if agent is not None:
            self._validate_agent(agent)
            if getattr(agent, "agent_id", None) != agent_id:
                raise LookupError("agent_identity_mismatch")
        return agent

    def available(self) -> tuple[str, ...]:
        for agent_id, agent in self._agents.items():
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RuntimeError("invalid_registered_agent_id")
            try:
                registered_id = self._validate_agent(agent)
            except TypeError as exc:
                raise RuntimeError("invalid_registered_agent") from exc
            if registered_id != agent_id:
                raise RuntimeError("agent_identity_mismatch")
        return tuple(sorted(self._agents))

    def default_id(self) -> str:
        """Return the sole deterministic route; fail closed when routing is ambiguous."""
        available = self.available()
        if len(available) != 1:
            raise LookupError("no unique default resource route")
        return available[0]

    def route(self, preferred: str | None = None):
        if preferred is not None:
            if not isinstance(preferred, str):
                raise TypeError("invalid_preferred_agent_id")
            if not preferred.strip():
                raise ValueError("invalid_preferred_agent_id")
            agent = self._agents.get(preferred)
            if agent is None:
                raise LookupError("requested agent unavailable")
            try:
                registered_id = self._validate_agent(agent)
            except TypeError as exc:
                raise LookupError("invalid_registered_agent") from exc
            if registered_id != preferred:
                raise LookupError("agent_identity_mismatch")
            return agent
        available = self.available()
        if len(available) == 1:
            return self._agents[available[0]]
        raise LookupError("no unambiguous resource route")
