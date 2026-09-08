"""Bounded skill registry for NORYX7 agents.

Skills describe capabilities; they do not grant authority. Every execution
still crosses the canonical authorization/runtime boundaries. This keeps the
agent extensible across software engineering, science, research and defensive
cybersecurity without coupling the Agent Core to a particular model.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Mapping

MAX_SKILLS = 1024
MAX_NAME = 128
MAX_DESCRIPTION = 2048


def _default_skill_handler(*_args: object, **_kwargs: object) -> object:
    """Compatibility no-op for declarative skills without an execution hook."""
    return None


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    handler: Callable[..., object] = _default_skill_handler
    risk_class: str = "normal"
    requires_authorization: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > MAX_NAME:
            raise ValueError("invalid_skill_name")
        if not isinstance(self.description, str) or not self.description.strip() or len(self.description) > MAX_DESCRIPTION:
            raise ValueError("invalid_skill_description")
        if not callable(self.handler):
            raise TypeError("skill_handler_required")
        if not isinstance(self.risk_class, str) or not self.risk_class.strip():
            raise ValueError("invalid_skill_risk_class")
        if not isinstance(self.requires_authorization, bool):
            raise TypeError("requires_authorization_must_be_bool")


class AgentSkillRegistry:
    """Thread-safe, bounded registry; registration never implies permission."""

    def __init__(self, *, max_skills: int = MAX_SKILLS) -> None:
        if isinstance(max_skills, bool) or not isinstance(max_skills, int) or not 1 <= max_skills <= MAX_SKILLS:
            raise ValueError("invalid_max_skills")
        self._max_skills = max_skills
        self._skills: dict[str, AgentSkill] = {}
        self._lock = RLock()

    def register(self, skill: AgentSkill) -> None:
        if not isinstance(skill, AgentSkill):
            raise TypeError("agent_skill_required")
        with self._lock:
            if skill.name in self._skills:
                raise ValueError("skill_already_registered")
            if len(self._skills) >= self._max_skills:
                raise RuntimeError("skill_registry_capacity_exceeded")
            self._skills[skill.name] = skill

    def has(self, name: str) -> bool:
        """Return whether a skill is registered without raising on lookup."""
        if not isinstance(name, str) or not name.strip():
            return False
        with self._lock:
            return name in self._skills

    def get(self, name: str) -> AgentSkill:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("skill_name_required")
        with self._lock:
            try:
                return self._skills[name]
            except KeyError as exc:
                raise KeyError("skill_not_registered") from exc

    def describe(self) -> Mapping[str, str]:
        with self._lock:
            return {name: skill.description for name, skill in sorted(self._skills.items())}

    def snapshot(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._skills))
