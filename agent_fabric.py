from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable

from .agent_core import AgentCore, AgentInput, AgentPhase, AgentResponse
from .agent_skills import AgentSkillRegistry
from .identity import AgentIdentity, IdentityRegistry

MAX_FABRIC_AGENTS = 1024
_PRINCIPAL_CONTEXT_KEY = "noryx7_principal_id"

@dataclass(frozen=True)
class AgentBinding:
    agent: AgentCore
    identity: AgentIdentity
    skills: tuple[str, ...]
    def __post_init__(self):
        if not isinstance(self.agent, AgentCore): raise TypeError("agent must be AgentCore")
        if not isinstance(self.identity, AgentIdentity): raise TypeError("identity must be AgentIdentity")
        if self.identity.agent_id != self.agent.agent_id: raise ValueError("agent identity mismatch")
        if not self.identity.is_well_formed(): raise ValueError("invalid agent identity")
        if not self.skills or len(set(self.skills)) != len(self.skills) or any(not isinstance(s, str) or not s for s in self.skills): raise ValueError("invalid agent skills")

class AgentFabric:
    """Bounded native-agent fabric with identity, skill and principal authorization gates."""
    def __init__(self, skills: AgentSkillRegistry, identities: IdentityRegistry, authorize_principal: Callable[[str, AgentBinding, AgentInput], bool], max_agents: int = MAX_FABRIC_AGENTS) -> None:
        if not isinstance(skills, AgentSkillRegistry) or not isinstance(identities, IdentityRegistry) or not callable(authorize_principal): raise TypeError("invalid fabric dependencies")
        if not isinstance(max_agents, int) or isinstance(max_agents, bool) or max_agents < 1 or max_agents > MAX_FABRIC_AGENTS: raise ValueError("invalid fabric capacity")
        self._skills, self._identities, self._authorize_principal, self._max_agents = skills, identities, authorize_principal, max_agents; self._bindings = {}; self._lock = RLock()
    def register(self, binding: AgentBinding) -> None:
        if not isinstance(binding, AgentBinding): raise TypeError("binding must be AgentBinding")
        for skill in binding.skills:
            if not self._skills.has(skill): raise ValueError("unknown agent skill")
        if not self._identities.is_trusted(binding.identity): raise PermissionError("agent identity is not trusted")
        with self._lock:
            if binding.agent.agent_id in self._bindings: raise ValueError("duplicate agent")
            if len(self._bindings) >= self._max_agents: raise OverflowError("agent fabric capacity exceeded")
            self._bindings[binding.agent.agent_id] = binding
    def dispatch(self, principal_id: str, request: AgentInput, required_skill: str | None = None) -> AgentResponse:
        if not isinstance(principal_id, str) or not principal_id: raise ValueError("principal_id must be non-empty")
        if not isinstance(request, AgentInput): raise TypeError("request must be AgentInput")
        if required_skill is not None and not self._skills.has(required_skill): raise ValueError("unknown agent skill")
        context_principal = request.context.get(_PRINCIPAL_CONTEXT_KEY)
        if context_principal is not None and context_principal != principal_id: raise PermissionError("principal spoofing rejected")
        bound_context = dict(request.context); bound_context[_PRINCIPAL_CONTEXT_KEY] = principal_id; bound_request = AgentInput(request.content, request.mode, bound_context)
        with self._lock: candidates = tuple(self._bindings[key] for key in sorted(self._bindings))
        for binding in candidates:
            if binding.agent.phase is AgentPhase.FAILED: continue
            if required_skill is not None and required_skill not in binding.skills: continue
            if not self._identities.is_trusted(binding.identity): continue
            try: authorized = bool(self._authorize_principal(principal_id, binding, bound_request))
            except Exception: authorized = False
            if not authorized: continue
            return binding.agent.run(bound_request)
        raise PermissionError("no_authorized_agent")
