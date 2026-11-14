import pytest

from core.agent_skills import AgentSkill, AgentSkillRegistry


def test_skill_registration_is_bounded_and_deterministic():
    registry = AgentSkillRegistry(max_skills=2)
    registry.register(AgentSkill("python", "software engineering", lambda: "ok"))
    registry.register(AgentSkill("cybersecurity", "defensive security analysis", lambda: "ok", risk_class="high"))
    assert registry.snapshot() == ("cybersecurity", "python")
    with pytest.raises(RuntimeError, match="capacity"):
        registry.register(AgentSkill("science", "scientific analysis", lambda: "ok"))


def test_registration_does_not_imply_authority():
    registry = AgentSkillRegistry()
    skill = AgentSkill("network-analysis", "authorized defensive network analysis", lambda: "ok", risk_class="high")
    registry.register(skill)
    assert registry.get("network-analysis").requires_authorization is True


def test_duplicate_skill_is_rejected():
    registry = AgentSkillRegistry()
    registry.register(AgentSkill("research", "research", lambda: None))
    with pytest.raises(ValueError, match="already_registered"):
        registry.register(AgentSkill("research", "research", lambda: None))
