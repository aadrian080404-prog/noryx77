import pytest

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult


KEY = b"k" * 32


def task(execution="exec-1"):
    return TaskSpec("task-1", "analysis", "solve", "input", execution_id=execution)


def result(agent, output="answer", execution="exec-1"):
    return AgentResult(agent, "task-1", "completed", output, VerificationResult(True, "agent_result", "ok"), execution)


def test_independent_peer_evidence_is_sealed_and_admitted():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a"), result("agent-b")
    evidence = pair.evidence(t, first, "agent-b", "challenge-the-output")
    assert pair.verify_evidence(evidence, task=t)
    assert pair.admit_consensus(t, first, second, evidence).valid


def test_admitted_evidence_cannot_be_replayed():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a"), result("agent-b")
    evidence = pair.evidence(t, first, "agent-b", "challenge")
    assert pair.admit_consensus(t, first, second, evidence).valid
    replay = pair.admit_consensus(t, first, second, evidence)
    assert not replay.valid
    assert replay.reason == "evidence_replay_rejected"


def test_tampered_evidence_fails_closed():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge")
    tampered = type(evidence)(**{**evidence.__dict__, "target_agent_id": "agent-c"})
    assert not pair.verify_evidence(tampered, task=t)


def test_cross_runtime_and_cross_execution_are_rejected():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge")
    other_runtime = PeerCollaboration("runtime-2", t.execution_id, seal_key=KEY)
    other_execution = PeerCollaboration("runtime-1", "exec-2", seal_key=KEY)
    assert not other_runtime.verify_evidence(evidence, task=t)
    assert not other_execution.verify_evidence(evidence, task=t)


def test_same_agent_cannot_count_as_peer():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    with pytest.raises(ValueError, match="invalid_peer_identity"):
        pair.evidence(t, result("agent-a"), "agent-a", "challenge")


def test_unverified_result_cannot_enter_collaboration():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    bad = AgentResult("agent-a", t.task_id, "completed", "answer", VerificationResult(False, "agent_result", "bad"), t.execution_id)
    with pytest.raises(ValueError, match="unverified_source_result"):
        pair.evidence(t, bad, "agent-b", "challenge")


def test_evidence_cannot_be_retargeted_to_different_task():
    t = task()
    pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge")
    other = TaskSpec("task-2", "analysis", "other", "input", execution_id=t.execution_id)
    assert not pair.verify_evidence(evidence, task=other)
