import pytest

from .agent_core import AgentCore, AgentInput, AgentPhase, AgentPlan, AgentResponse, InteractionMode
from .agent_fabric import AgentBinding, AgentFabric
from .agent_skills import AgentSkill, AgentSkillRegistry
from .identity import AgentIdentityAuthority, IdentityRegistry

class Brain:
    def understand(self, request): return type("C", (), {"objective": request.content, "input": request, "facts": {}})()
    def plan(self, context): return AgentPlan(("answer",))
    def act(self, step, context): return "ok"
    def verify(self, step, result, context): return True
    def reflect(self, context, results): return "done"
    def respond(self, context, reflection, results): return AgentResponse("ok", context.input.mode, verified=True)

def make_fabric(agent_ids=("agent-1",)):
    skills = AgentSkillRegistry(); skills.register(AgentSkill("general", "general capability")); identities = IdentityRegistry(); agents = []
    for agent_id in agent_ids:
        identity, _ = AgentIdentityAuthority.generate(agent_id); identities.register(identity); agent = AgentCore(agent_id, Brain()); agents.append((agent, identity))
    fabric = AgentFabric(skills, identities, lambda principal, binding, request: principal == "owner")
    for agent, identity in agents: fabric.register(AgentBinding(agent, identity, ("general",)))
    return fabric, agents

def test_principal_authorization_is_required():
    fabric, _ = make_fabric(); fabric._authorize_principal = lambda *args: False
    with pytest.raises(PermissionError, match="no_authorized_agent"): fabric.dispatch("owner", AgentInput("hello"), "general")

def test_verified_agent_dispatches_with_bound_principal():
    fabric, agents = make_fabric(); response = fabric.dispatch("owner", AgentInput("hello"), "general")
    assert response.verified and agents[0][0].phase is AgentPhase.IDLE

def test_principal_is_bound_into_request_context():
    class ContextBrain(Brain):
        def understand(self, request):
            assert request.context["noryx7_principal_id"] == "owner"
            return super().understand(request)
    skills = AgentSkillRegistry(); skills.register(AgentSkill("general", "general capability")); identities = IdentityRegistry(); identity, _ = AgentIdentityAuthority.generate("agent-1"); identities.register(identity); agent = AgentCore("agent-1", ContextBrain()); fabric = AgentFabric(skills, identities, lambda *args: True); fabric.register(AgentBinding(agent, identity, ("general",))); fabric.dispatch("owner", AgentInput("hello"), "general")

def test_principal_spoofing_is_rejected():
    fabric, _ = make_fabric()
    with pytest.raises(PermissionError, match="spoofing"): fabric.dispatch("owner", AgentInput("hello", context={"noryx7_principal_id": "attacker"}), "general")

def test_revoked_identity_is_rejected():
    fabric, agents = make_fabric(); identities = fabric._identities; identities.revoke("agent-1")
    with pytest.raises(PermissionError, match="no_authorized_agent"): fabric.dispatch("owner", AgentInput("hello"), "general")

def test_failed_agent_is_skipped_and_healthy_agent_handles_request():
    fabric, agents = make_fabric(("agent-1", "agent-2")); failed = agents[0][0]; healthy = agents[1][0]
    failed._phase = AgentPhase.FAILED
    response = fabric.dispatch("owner", AgentInput("hello"), "general")
    assert response.verified and healthy.phase is AgentPhase.IDLE

def test_failed_agent_requires_explicit_reset():
    fabric, agents = make_fabric(); agent = agents[0][0]; agent._phase = AgentPhase.FAILED; agent._last_failure = "RuntimeError"
    with pytest.raises(RuntimeError, match="reset"): agent.run(AgentInput("hello"))
    agent.reset(); assert agent.phase is AgentPhase.IDLE and agent.last_failure is None
