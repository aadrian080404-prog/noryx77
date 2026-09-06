from .agent_core import AgentContext, AgentCore, AgentInput, AgentPlan, AgentResponse
from .agent_fabric import AgentBinding, AgentFabric
from .agent_skills import AgentSkill, AgentSkillRegistry
from .identity import AgentIdentityAuthority, IdentityRegistry


class Brain:
    def understand(self, request):
        return AgentContext("objective", request)

    def plan(self, context):
        return AgentPlan(("action:skill",))

    def act(self, context, step):
        return "ok"

    def verify(self, context, step, result):
        return result == "ok"

    def reflect(self, context, results):
        return "verified"

    def respond(self, context, reflection, mode):
        return AgentResponse("done", mode, verified=True)


def make_fabric():
    identity, _ = AgentIdentityAuthority.generate("agent-a")
    identities = IdentityRegistry()
    identities.register(identity)
    skills = AgentSkillRegistry()
    skills.register(AgentSkill("skill", "test capability", lambda: "ok"))
    agent = AgentCore(agent_id="agent-a", brain=Brain(), authorize=lambda _c, _s: True)
    fabric = AgentFabric(skills=skills, identities=identities,
                         authorize_principal=lambda principal, binding, _request: principal == "owner")
    fabric.register(AgentBinding(agent, identity, ("skill",)))
    return fabric, identities, identity


def test_dispatch_requires_principal_authorization():
    fabric, _, _ = make_fabric()
    try:
        fabric.dispatch(principal_id="other", request=AgentInput("hello"), required_skill="skill")
    except PermissionError as exc:
        assert str(exc) == "no_authorized_agent"
    else:
        raise AssertionError("unauthorized principal was dispatched")


def test_dispatch_runs_verified_agent():
    fabric, _, _ = make_fabric()
    assert fabric.dispatch(principal_id="owner", request=AgentInput("hello"), required_skill="skill") == "done"


def test_principal_is_bound_into_agent_context():
    fabric, _, _ = make_fabric()
    seen = []
    fabric._authorize_principal = lambda principal, binding, request: seen.append(request.context["noryx7_principal_id"]) or principal == "owner"
    assert fabric.dispatch(principal_id="owner", request=AgentInput("hello"), required_skill="skill") == "done"
    assert seen == ["owner"]


def test_principal_context_spoofing_is_rejected():
    fabric, _, _ = make_fabric()
    try:
        fabric.dispatch(principal_id="owner", request=AgentInput("hello", context={"noryx7_principal_id": "other"}))
    except PermissionError as exc:
        assert str(exc) == "principal_context_mismatch"
    else:
        raise AssertionError("spoofed principal context was accepted")


def test_revoked_identity_is_rejected():
    fabric, identities, identity = make_fabric()
    identities.revoke(identity.agent_id)
    try:
        fabric.dispatch(principal_id="owner", request=AgentInput("hello"), required_skill="skill")
    except PermissionError as exc:
        assert str(exc) == "no_authorized_agent"
    else:
        raise AssertionError("revoked agent was dispatched")
