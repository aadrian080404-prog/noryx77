import pytest

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult
from .peer_execution import PeerExecutionCoordinator


KEY = b"p" * 32


def task(execution="exec-peer"):
    return TaskSpec("task-peer", "analysis", "solve", "input", execution_id=execution)


def result(agent_id, output="same", execution="exec-peer"):
    return AgentResult(agent_id, "task-peer", "completed", output, VerificationResult(True, "agent_result", "verified"), execution)


class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id


def run(agent, task):
    return result(agent.agent_id)


def test_peer_execution_requires_independent_verified_peers():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY))
    outcome = coordinator.execute(t, Agent("a"), Agent("b"), run)
    assert outcome.collaboration.valid
    assert outcome.first.agent_id == "a"
    assert outcome.second.agent_id == "b"


def test_peer_execution_rejects_same_identity():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY))
    with pytest.raises(ValueError, match="peer_identity_not_independent"):
        coordinator.execute(t, Agent("a"), Agent("a"), run)


def test_peer_execution_rejects_cross_execution():
    t = task("exec-a")
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", "exec-b", seal_key=KEY))
    with pytest.raises(PermissionError, match="execution_identity_mismatch"):
        coordinator.execute(t, Agent("a"), Agent("b"), run)


def test_peer_execution_rejects_forged_agent_result():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY))

    def forged(agent, task):
        return result("forged")

    with pytest.raises(PermissionError, match="first_result_identity_mismatch"):
        coordinator.execute(t, Agent("a"), Agent("b"), forged)


def test_peer_execution_rejects_disagreement_without_revision():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY))

    def disagree(agent, task):
        return result(agent.agent_id, "different" if agent.agent_id == "b" else "same")

    with pytest.raises(PermissionError, match="peer_disagreement_requires_resolution"):
        coordinator.execute(t, Agent("a"), Agent("b"), disagree)
