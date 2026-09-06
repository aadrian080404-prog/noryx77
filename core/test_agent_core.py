import pytest

from core.agent_core import (
    AgentContext,
    AgentCore,
    AgentInput,
    AgentOperatingManual,
    AgentPhase,
    AgentPlan,
    AgentResponse,
    InteractionMode,
    VoiceTransport,
)


class Brain:
    def understand(self, request):
        return AgentContext("solve", request)

    def plan(self, context):
        return AgentPlan(("step-a", "step-b"))

    def act(self, context, step):
        return step.upper()

    def verify(self, context, step, result):
        return result == step.upper()

    def reflect(self, context, results):
        return "verified"

    def respond(self, context, reflection, mode):
        return AgentResponse("done", mode, verified=True)


def test_manual_is_complete_and_ordered():
    AgentOperatingManual.validate()
    assert AgentOperatingManual.PHASES == (
        AgentPhase.UNDERSTANDING, AgentPhase.PLANNING, AgentPhase.AUTHORIZING,
        AgentPhase.ACTING, AgentPhase.OBSERVING, AgentPhase.VERIFYING,
        AgentPhase.REFLECTING, AgentPhase.RESPONDING,
    )


def test_agent_executes_same_core_for_text_and_voice_modes():
    agent = AgentCore(agent_id="a1", brain=Brain(), authorize=lambda context, step: True)
    assert agent.run(AgentInput("hello", InteractionMode.TEXT)) == "done"
    assert agent.phase is AgentPhase.IDLE
    assert agent.run(AgentInput("hello", InteractionMode.VOICE)) == "done"


def test_authorization_denial_prevents_action():
    calls = []
    class DeniedBrain(Brain):
        def act(self, context, step):
            calls.append(step)
            return super().act(context, step)
    agent = AgentCore(agent_id="a1", brain=DeniedBrain(), authorize=lambda context, step: False)
    with pytest.raises(PermissionError, match="agent_action_denied"):
        agent.run(AgentInput("hello"))
    assert calls == []
    assert agent.phase is AgentPhase.FAILED


def test_failed_result_cannot_become_response():
    class BadVerifier(Brain):
        def verify(self, context, step, result):
            return False
    agent = AgentCore(agent_id="a1", brain=BadVerifier())
    with pytest.raises(PermissionError, match="agent_result_verification_failed"):
        agent.run(AgentInput("hello"))


def test_voice_transport_is_adapter_not_a_second_brain():
    spoken = []
    transport = VoiceTransport(synthesize=lambda text: spoken.append(text) or b"audio")
    response = AgentResponse("hello", InteractionMode.VOICE, verified=True)
    assert transport.encode(response) == b"audio"
    assert spoken == ["hello"]


def test_invalid_response_fails_closed():
    class UnverifiedBrain(Brain):
        def respond(self, context, reflection, mode):
            return AgentResponse("unsafe", mode, verified=False)
    agent = AgentCore(agent_id="a1", brain=UnverifiedBrain())
    with pytest.raises(PermissionError, match="agent_response_unverified"):
        agent.run(AgentInput("hello"))
