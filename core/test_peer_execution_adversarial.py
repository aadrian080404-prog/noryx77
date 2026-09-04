import pytest
from dataclasses import replace

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult
from .peer_execution import PeerChallenge, PeerExecutionCoordinator

KEY = b"q" * 32


def task(execution="exec-attack"):
    return TaskSpec("task-attack", "analysis", "solve", execution_id=execution)


def result(agent_id, output="same", execution="exec-attack", task_id="task-attack"):
    return AgentResult(agent_id, task_id, "completed", output, VerificationResult(True, "agent_result", "verified"), execution)


class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id


def test_revision_cannot_change_peer_pair():
    t = task()
    c = PeerExecutionCoordinator(PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY, max_rounds=1))

    def initial(agent, task):
        return result(agent.agent_id, "a" if agent.agent_id == "a" else "b")

    def swapped_pair(task, first, second, revision):
        return PeerChallenge(result("a", "resolved"), result("c", "resolved"), "reconsider")

    with pytest.raises(PermissionError, match="second_revision_result_identity_mismatch"):
        c.execute(t, Agent("a"), Agent("b"), initial, challenge=swapped_pair)


def test_revision_cannot_retarget_task():
    t = task()
    c = PeerExecutionCoordinator(PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY, max_rounds=1))

    def initial(agent, task):
        return result(agent.agent_id, agent.agent_id)

    def retarget(task, first, second, revision):
        return PeerChallenge(result("a", "resolved", task_id="other-task"), result("b", "resolved"), "reconsider")

    with pytest.raises(PermissionError, match="first_revision_result_identity_mismatch"):
        c.execute(t, Agent("a"), Agent("b"), initial, challenge=retarget)


def test_tampered_initial_verification_cannot_enter_collaboration():
    t = task()
    c = PeerExecutionCoordinator(PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY))

    def forged(agent, task):
        return replace(result(agent.agent_id), verification=VerificationResult(False, "agent_result", "forged"))

    with pytest.raises(PermissionError, match="first_result_unverified"):
        c.execute(t, Agent("a"), Agent("b"), forged)


def test_revision_cannot_skip_or_rollback_revision():
    t = task()
    collaboration = PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY, max_rounds=2)
    first, second = result("a", "a"), result("b", "b")

    initial = collaboration.evidence(
        t,
        first,
        "b",
        "initial-challenge",
        revision=0,
        target_output=second.output,
        target_verification=second.verification,
    )
    initial_digest = collaboration.evidence_digest(initial)
    revision_one = collaboration.evidence(
        t,
        result("a", "a1"),
        "b",
        "challenge-1",
        revision=1,
        previous_evidence_digest=initial_digest,
        target_output="b1",
        target_verification=second.verification,
    )
    revision_one_digest = collaboration.evidence_digest(revision_one)

    assert collaboration.verify_evidence(initial, task=t)
    assert collaboration.verify_evidence(revision_one, task=t)

    skipped = collaboration.evidence(
        t,
        result("a", "a2"),
        "b",
        "challenge-2",
        revision=2,
        previous_evidence_digest=initial_digest,
        target_output="b2",
        target_verification=second.verification,
    )
    assert not collaboration.verify_evidence(skipped, task=t)

    rollback = replace(revision_one, revision=0, previous_evidence_digest="")
    assert not collaboration.verify_evidence(rollback, task=t)
    assert collaboration.verify_evidence(revision_one, task=t)
    assert revision_one_digest == collaboration.evidence_digest(revision_one)


def test_evidence_seal_binds_challenge_and_revision():
    t = task()
    collaboration = PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY)
    first, second = result("a", "x"), result("b", "y")
    evidence = collaboration.evidence(t, first, "b", "challenge", target_output=second.output, target_verification=second.verification)
    assert collaboration.verify_evidence(evidence, task=t)
    assert not collaboration.verify_evidence(replace(evidence, challenge="attacker"), task=t)
    assert not collaboration.verify_evidence(replace(evidence, revision=1, previous_evidence_digest="0" * 64), task=t)


def test_runtime_binding_rejects_evidence_from_other_runtime():
    t = task()
    collaboration = PeerCollaboration("runtime-attack", t.execution_id, seal_key=KEY)
    evidence = collaboration.evidence(t, result("a", "x"), "b", "challenge", target_output="y", target_verification=result("b", "y").verification)
    forged = replace(evidence, runtime_id="other-runtime")
    assert not collaboration.verify_evidence(forged, task=t)
