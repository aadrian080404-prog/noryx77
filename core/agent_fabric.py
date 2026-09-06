"""Unified NORYX7 agent fabric.

This module binds the native AgentCore, skill registry, identity trust and
principal authorization into one deterministic dispatch boundary. Skills are
capabilities only; registration never grants authority. Concrete execution
continues through AgentCore's authorization/verification lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable

from .agent_core import AgentCore, AgentInput
from .agent_skills import AgentSkillRegistry
from .identity import AgentIdentity, IdentityRegistry

MAX_FABRIC_AGENTS = 1024


@dataclass(frozen=True)
class AgentBinding:
    agent: AgentCore
    identity: AgentIdentity
    skills: tuple[str, ...]

    def validate(self, skills: AgentSkillRegistry, identities: IdentityRegistry) -> None:
        if not isinstance(self.agent, AgentCore):
            raise TypeError("agent_core_required")
        if not isinstance(self.identity, AgentIdentity) or not self.identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        if self.identity.agent_id != self.agent.agent_id:
            raise ValueError("agent_identity_mismatch")
        if not identities.is_trusted(self.identity):
            raise PermissionError("agent_identity_not_trusted")
        if not isinstance(self.skills, tuple) or not self.skills:
            raise ValueError("agent_skills_required")
        if len(set(self.skills)) != len(self.skills):
            raise ValueError("duplicate_agent_skill")
        for skill in self.skills:
            skills.get(skill)


class AgentFabric:
    """Deterministic multi-agent dispatch with explicit trust boundaries."""

    def __init__(self, *, skills: AgentSkillRegistry, identities: IdentityRegistry,
                 authorize_principal: Callable[[str, AgentBinding, AgentInput], bool],
                 max_agents: int = MAX_FABRIC_AGENTS) -> None:
        if not isinstance(skills, AgentSkillRegistry):
            raise TypeError("skills_registry_required")
        if not isinstance(identities, IdentityRegistry):
            raise TypeError("identity_registry_required")
        if not callable(authorize_principal):
            raise TypeError("principal_authorizer_required")
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or not 1 <= max_agents <= MAX_FABRIC_AGENTS:
            raise ValueError("invalid_max_agents")
        self._skills = skills
        self._identities = identities
        self._authorize_principal = authorize_principal
        self._max_agents = max_agents
        self._bindings: dict[str, AgentBinding] = {}
        self._lock = RLock()

    def register(self, binding: AgentBinding) -> None:
        if not isinstance(binding, AgentBinding):
            raise TypeError("agent_binding_required")
        binding.validate(self._skills, self._identities)
        with self._lock:
            if binding.agent.agent_id in self._bindings:
                raise ValueError("agent_already_registered")
            if len(self._bindings) >= self._max_agents:
                raise RuntimeError("agent_fabric_capacity_exceeded")
            self._bindings[binding.agent.agent_id] = binding

    def dispatch(self, *, principal_id: str, request: AgentInput, required_skill: str | None = None) -> object:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("principal_id_required")
        if not isinstance(request, AgentInput):
            raise TypeError("agent_input_required")
        if required_skill is not None:
            self._skills.get(required_skill)
        with self._lock:
            candidates = tuple(self._bindings[name] for name in sorted(self._bindings))
        for binding in candidates:
            if required_skill is not None and required_skill not in binding.skills:
                continue
            if not self._identities.is_trusted(binding.identity):
                continue
            if not bool(self._authorize_principal(principal_id, binding, request)):
                continue
            return binding.agent.run(request)
        raise PermissionError("no_authorized_agent")

    def snapshot(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._bindings))
