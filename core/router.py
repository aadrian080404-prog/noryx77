from .agents import Agent
from .identity import AgentIdentity, IdentityRegistry


class ResourceRouter:
    """Selects registered agents and optionally enforces cryptographic identity trust."""

    def __init__(self, identity_registry: IdentityRegistry | None = None):
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise ValueError("invalid_identity_registry")
        self._identity_registry = identity_registry
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        agent_id = getattr(agent, "agent_id", None)
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("agent_id required")
        if agent_id in self._agents:
            raise ValueError("agent_id already registered")
        if self._identity_registry is not None:
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or identity.agent_id != agent_id:
                raise ValueError("agent_identity_required")
            if not self._identity_registry.is_trusted(identity):
                raise ValueError("agent_identity_untrusted")
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
            if self._identity_registry is not None:
                identity = getattr(agent, "identity", None)
                if not isinstance(identity, AgentIdentity) or not self._identity_registry.is_trusted(identity):
                    raise LookupError("agent_identity_untrusted")
            return agent
        if len(self._agents) == 1:
            agent = next(iter(self._agents.values()))
            if self._identity_registry is not None:
                identity = getattr(agent, "identity", None)
                if not isinstance(identity, AgentIdentity) or not self._identity_registry.is_trusted(identity):
                    raise LookupError("agent_identity_untrusted")
            return agent
        raise LookupError("no unambiguous resource route")

    @property
    def identity_registry(self) -> IdentityRegistry | None:
        return self._identity_registry

    def identity_is_trusted(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        if self._identity_registry is None:
            return True
        identity = getattr(agent, "identity", None)
        return isinstance(identity, AgentIdentity) and self._identity_registry.is_trusted(identity)
