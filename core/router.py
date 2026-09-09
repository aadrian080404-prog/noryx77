from __future__ import annotations

import hashlib

from .agents import Agent
from .identity import AgentIdentity, IdentityRegistry


class ResourceRouter:
    """Select registered agents while enforcing identity and canonical capability trust."""

    def __init__(self, identity_registry: IdentityRegistry | None = None, system_fabric=None):
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise ValueError("invalid_identity_registry")
        self._identity_registry = identity_registry
        self._system_fabric = system_fabric
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

    def attach_system_fabric(self, system_fabric) -> None:
        """Attach the canonical authorization boundary after runtime construction."""
        if system_fabric is None or not callable(getattr(system_fabric, "authorize_agent", None)):
            raise ValueError("invalid_system_fabric")
        self._system_fabric = system_fabric

    def _authorize_route(self, agent: Agent, required_capability: str) -> None:
        if not isinstance(required_capability, str) or not required_capability.strip():
            raise ValueError("required_capability must be non-empty")
        identity = getattr(agent, "identity", None)
        if self._identity_registry is not None:
            if not isinstance(identity, AgentIdentity) or not self._identity_registry.is_trusted(identity):
                raise LookupError("agent_identity_untrusted")
        if self._system_fabric is not None:
            if not isinstance(identity, AgentIdentity):
                raise LookupError("agent_identity_required")
            try:
                self._system_fabric.authorize_agent(identity, required_capability)
            except Exception as exc:
                raise PermissionError("agent_route_not_authorized") from exc

    def route(self, preferred: str | None = None, *, required_capability: str = "execute"):
        if preferred:
            agent = self._agents.get(preferred)
            if agent is None:
                raise LookupError("requested agent unavailable")
            self._authorize_route(agent, required_capability)
            return agent
        if len(self._agents) == 1:
            agent = next(iter(self._agents.values()))
            self._authorize_route(agent, required_capability)
            return agent
        raise LookupError("no unambiguous resource route")

    def route_provenance(self, agent: Agent, *, required_capability: str = "execute") -> dict[str, str]:
        """Return digest-only route provenance after re-authorizing the selected agent."""
        self._authorize_route(agent, required_capability)
        identity = getattr(agent, "identity", None)
        agent_id = getattr(agent, "agent_id", "")
        identity_digest = ""
        if isinstance(identity, AgentIdentity):
            identity_digest = hashlib.sha256(identity.public_key).hexdigest()
        return {
            "agent_id": agent_id,
            "identity_digest": identity_digest,
            "capability": required_capability,
        }

    @property
    def identity_registry(self) -> IdentityRegistry | None:
        return self._identity_registry

    @property
    def system_fabric(self):
        return self._system_fabric

    def identity_is_trusted(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        if self._identity_registry is None:
            return True
        identity = getattr(agent, "identity", None)
        return isinstance(identity, AgentIdentity) and self._identity_registry.is_trusted(identity)
