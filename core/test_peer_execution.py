import pytest

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult
from .peer_execution import PeerChallenge, PeerExecutionCoordinator


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


def test_peer_execution_resolves_disagreement_with_one_bounded_revision():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY, max_rounds=1))
    calls = {"count": 0}

    def disagree_then_resolve(agent, task):
        return result(agent.agent_id, "same" if calls["count"] > 1 else ("first" if agent.agent_id == "a" else "second"))

    # Initial independent execution deliberately disagrees.
    def initial(agent, task):
        return result(agent.agent_id, "first" if agent.agent_id == "a" else "second")

    def revise(task, first, second, revision):
        calls["count"] += 1
        assert revision == 1
        assert first.output == "first"
        assert second.output == "second"
        return PeerChallenge(result("a", "resolved"), result("b", "resolved"), "Re-evaluate the disagreement against the shared objective.")

    outcome = coordinator.execute(t, Agent("a"), Agent("b"), initial, challenge=revise)
    assert outcome.collaboration.valid
    assert outcome.first.output == "resolved"
    assert outcome.second.output == "resolved"
    assert calls["count"] == 1


def test_peer_execution_rejects_revision_identity_swap():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY, max_rounds=1))

    def initial(agent, task):
        return result(agent.agent_id, "first" if agent.agent_id == "a" else "second")

    def swap(task, first, second, revision):
        return PeerChallenge(result("b", "resolved"), result("a", "resolved"), "challenge")

    with pytest.raises(PermissionError, match="first_revision_result_identity_mismatch"):
        coordinator.execute(t, Agent("a"), Agent("b"), initial, challenge=swap)


def test_peer_execution_rejects_revision_cross_execution():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY, max_rounds=1))

    def initial(agent, task):
        return result(agent.agent_id, "first" if agent.agent_id == "a" else "second")

    def forged_revision(task, first, second, revision):
        return PeerChallenge(result("a", "resolved", "other-execution"), result("b", "resolved"), "challenge")

    with pytest.raises(PermissionError, match="first_revision_result_identity_mismatch"):
        coordinator.execute(t, Agent("a"), Agent("b"), initial, challenge=forged_revision)


def test_peer_execution_enforces_max_rounds():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY, max_rounds=1))
    calls = []

    def initial(agent, task):
        return result(agent.agent_id, "first" if agent.agent_id == "a" else "second")

    def unresolved(task, first, second, revision):
        calls.append(revision)
        return PeerChallenge(result("a", f"a-{revision}"), result("b", f"b-{revision}"), f"challenge-{revision}")

    with pytest.raises(PermissionError, match="peer_disagreement_unresolved"):
        coordinator.execute(t, Agent("a"), Agent("b"), initial, challenge=unresolved)
    assert calls == [1]


def test_peer_execution_rejects_invalid_challenge_response():
    t = task()
    coordinator = PeerExecutionCoordinator(PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY, max_rounds=1))

    def initial(agent, task):
        return result(agent.agent_id, "first" if agent.agent_id == "a" else "second")

    def invalid(task, first, second, revision):
        return (first, second)

    with pytest.raises(ValueError, match="invalid_peer_challenge"):
        coordinator.execute(t, Agent("a"), Agent("b"), initial, challenge=invalid)
