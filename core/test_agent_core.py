import pytest

from core.agent_core import AgentContext, AgentCore, AgentInput, AgentOperatingManual, AgentPhase, AgentPlan, AgentResponse, InteractionMode, TextTransport, VoiceTransport


class Brain:
    def understand(self, request): return AgentContext("solve", request)
    def plan(self, context): return AgentPlan(("step-a", "step-b"))
    def act(self, step, context): return step.upper()
    def verify(self, step, result, context): return result == step.upper()
    def reflect(self, context, results): return "verified"
    def respond(self, context, reflection, results): return AgentResponse("done", context.input.mode, verified=True)


def test_manual_is_complete_and_ordered():
    assert AgentOperatingManual.PHASES == (AgentPhase.UNDERSTANDING, AgentPhase.PLANNING, AgentPhase.AUTHORIZING, AgentPhase.ACTING, AgentPhase.OBSERVING, AgentPhase.VERIFYING, AgentPhase.REFLECTING, AgentPhase.RESPONDING)


def test_agent_executes_same_core_for_text_and_voice_modes():
    agent = AgentCore("a1", Brain(), authorize=lambda step, context: True)
    assert agent.run(AgentInput("hello", InteractionMode.TEXT)).content == "done"
    assert agent.phase is AgentPhase.IDLE
    assert agent.run(AgentInput("hello", InteractionMode.VOICE)).content == "done"


def test_authorization_denial_prevents_action():
    calls = []
    class DeniedBrain(Brain):
        def act(self, step, context): calls.append(step); return super().act(step, context)
    agent = AgentCore("a1", DeniedBrain(), authorize=lambda step, context: False)
    with pytest.raises(PermissionError, match="agent_action_denied"): agent.run(AgentInput("hello"))
    assert calls == [] and agent.phase is AgentPhase.FAILED


def test_failed_result_cannot_become_response():
    class BadVerifier(Brain):
        def verify(self, step, result, context): return False
    agent = AgentCore("a1", BadVerifier())
    with pytest.raises(PermissionError, match="agent_result_unverified"): agent.run(AgentInput("hello"))
    assert agent.phase is AgentPhase.FAILED


def test_transports_preserve_verified_response():
    response = AgentResponse("hello", InteractionMode.VOICE, verified=True)
    assert TextTransport().deliver(response) == response
    assert VoiceTransport().deliver(response) == response


def test_invalid_response_fails_closed():
    class UnverifiedBrain(Brain):
        def respond(self, context, reflection, results): return AgentResponse("unsafe", context.input.mode, verified=False)
    agent = AgentCore("a1", UnverifiedBrain())
    with pytest.raises(PermissionError, match="agent_response_unverified"): agent.run(AgentInput("hello"))


def test_failed_agent_requires_explicit_reset():
    agent = AgentCore("a1", Brain())
    agent._phase = AgentPhase.FAILED; agent._last_failure = "RuntimeError"
    with pytest.raises(RuntimeError, match="reset"): agent.run(AgentInput("hello"))
    agent.reset()
    assert agent.phase is AgentPhase.IDLE and agent.last_failure is None
