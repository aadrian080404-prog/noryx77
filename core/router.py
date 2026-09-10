from .agents import Agent
from .identity import AgentIdentity, IdentityRegistry


class ResourceRouter:
    """Select registered agents and optionally enforce cryptographic identity trust."""

    def __init__(self, identity_registry: IdentityRegistry | None = None, system_fabric=None):
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise ValueError("invalid_identity_registry")
        self._identity_registry = identity_registry
        self._system_fabric = system_fabric
        self._agents: dict[str, Agent] = {}

    @property
    def system_fabric(self):
        return self._system_fabric

    @system_fabric.setter
    def system_fabric(self, value) -> None:
        self._system_fabric = value

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
        if len(self._agents) != 1:
            raise LookupError("no unique default resource route")
        return next(iter(self._agents))

    def _authorize(self, agent, required_capability: str | None) -> None:
        if required_capability is None:
            return
        if not isinstance(required_capability, str) or not required_capability.strip():
            raise ValueError("required_capability_invalid")
        if self._system_fabric is None:
            raise PermissionError("canonical_system_fabric_required")
        identity = getattr(agent, "identity", None)
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise PermissionError("agent_identity_required")
        self._system_fabric.authorize_agent(identity, required_capability)

    def route(self, preferred: str | None = None, *, required_capability: str | None = None):
        if preferred:
            agent = self._agents.get(preferred)
            if agent is None:
                raise LookupError("requested agent unavailable")
        elif len(self._agents) == 1:
            agent = next(iter(self._agents.values()))
        else:
            raise LookupError("no unambiguous resource route")
        if self._identity_registry is not None:
            identity = getattr(agent, "identity", None)
            if not isinstance(identity, AgentIdentity) or not self._identity_registry.is_trusted(identity):
                raise LookupError("agent_identity_untrusted")
        self._authorize(agent, required_capability)
        return agent

    def identity_is_trusted(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        if self._identity_registry is None:
            return True
        identity = getattr(agent, "identity", None)
        return isinstance(identity, AgentIdentity) and self._identity_registry.is_trusted(identity)
