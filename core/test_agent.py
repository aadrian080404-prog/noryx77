from dataclasses import dataclass

import pytest

from .agent import AgentCore, AgentInput, AgentPhase, AgentPlan, InputModality, OutputModality
from .identity import AgentIdentityAuthority


class Cognition:
    def understand(self, agent_input):
        return {"query": str(agent_input.payload)}

    def plan(self, understanding):
        return AgentPlan(understanding["query"], ("respond",))

    def respond(self, understanding, result):
        return f"response:{understanding['query']}"


class Speech:
    def transcribe(self, audio):
        return "hello from voice"

    def synthesize(self, text):
        return f"audio:{text}"


class Verifier:
    def verify(self, value, *, stage):
        return stage == "agent_result"


class Memory:
    def __init__(self):
        self.items = []

    def recall(self, principal_id, session_id, query):
        return tuple(self.items)

    def remember(self, principal_id, session_id, value):
        self.items.append(value)


def make_agent(**kwargs):
    identity, _ = AgentIdentityAuthority.generate("agent-test")
    return AgentCore(identity=identity, cognition=Cognition(), verifier=Verifier(), **kwargs)


def test_text_lifecycle_is_verified_and_returns_to_ready():
    agent = make_agent()
    response = agent.process(AgentInput(InputModality.TEXT, "hello", "s1", "p1"))
    assert response.agent_id == "agent-test"
    assert response.principal_id == "p1"
    assert response.modality is OutputModality.TEXT
    assert response.verified is True
    assert agent.phase is AgentPhase.READY
    assert agent.turns == 1


def test_voice_input_uses_speech_adapter_without_changing_agent_core():
    agent = make_agent(speech=Speech())
    response = agent.process(AgentInput(InputModality.VOICE, b"audio", "s1", "p1"))
    assert response.text == "response:hello from voice"
    assert agent.speak(response) == "audio:response:hello from voice"


def test_voice_requires_explicit_speech_adapter():
    agent = make_agent()
    with pytest.raises(PermissionError, match="voice_input_unavailable"):
        agent.process(AgentInput(InputModality.VOICE, b"audio", "s1", "p1"))
    assert agent.phase is AgentPhase.FAILED


def test_actions_cannot_execute_without_both_authorizer_and_executor():
    identity, _ = AgentIdentityAuthority.generate("agent-test")

    class ActionCognition(Cognition):
        def plan(self, understanding):
            return AgentPlan(understanding["query"], ("action:network_scan",))

    with pytest.raises(ValueError, match="authorizer_and_executor"):
        AgentCore(identity=identity, cognition=ActionCognition(), verifier=Verifier(), authorizer=object())


def test_authorized_action_executes_and_is_verified():
    calls = []

    class Authorizer:
        def authorize(self, agent_id, principal_id, action):
            return agent_id == "agent-test" and principal_id == "p1" and action == "network_scan"

    class Executor:
        def execute(self, agent_id, principal_id, action):
            calls.append((agent_id, principal_id, action))
            return {"status": "ok"}

    class ActionCognition(Cognition):
        def plan(self, understanding):
            return AgentPlan(understanding["query"], ("action:network_scan",))

    agent = make_agent(authorizer=Authorizer(), executor=Executor())
    agent.cognition = ActionCognition()
    response = agent.process(AgentInput(InputModality.TEXT, "scan", "s1", "p1"))
    assert calls == [("agent-test", "p1", "network_scan")]
    assert response.verified is True


def test_denied_action_fails_closed_before_executor():
    calls = []

    class Authorizer:
        def authorize(self, agent_id, principal_id, action):
            return False

    class Executor:
        def execute(self, *args):
            calls.append(args)
            return "must-not-run"

    class ActionCognition(Cognition):
        def plan(self, understanding):
            return AgentPlan(understanding["query"], ("action:network_scan",))

    agent = make_agent(authorizer=Authorizer(), executor=Executor())
    agent.cognition = ActionCognition()
    with pytest.raises(PermissionError, match="agent_action_denied"):
        agent.process(AgentInput(InputModality.TEXT, "scan", "s1", "p1"))
    assert calls == []


def test_memory_is_principal_and_session_scoped_at_interface_boundary():
    memory = Memory()
    agent = make_agent(memory=memory)
    response = agent.process(AgentInput(InputModality.TEXT, "remember", "s1", "p1"))
    assert response.verified
    assert len(memory.items) == 1


def test_turn_budget_is_bounded():
    agent = make_agent(max_turns=1)
    agent.process(AgentInput(InputModality.TEXT, "one", "s1", "p1"))
    with pytest.raises(RuntimeError, match="turn_budget"):
        agent.process(AgentInput(InputModality.TEXT, "two", "s1", "p1"))


def test_pause_and_resume_are_explicit():
    agent = make_agent()
    agent.pause()
    assert agent.phase is AgentPhase.PAUSED
    with pytest.raises(PermissionError, match="agent_paused"):
        agent.process(AgentInput(InputModality.TEXT, "x", "s1", "p1"))
    agent.resume()
    assert agent.phase is AgentPhase.READY
