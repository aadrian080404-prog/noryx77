import pytest

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult


KEY = b"k" * 32


def task(execution="exec-1"):
    return TaskSpec("task-1", "analysis", "solve", "input", execution_id=execution)


def result(agent, output="answer", execution="exec-1"):
    return AgentResult(agent, "task-1", "completed", output, VerificationResult(True, "agent_result", "ok"), execution)


def test_independent_peer_evidence_is_sealed_and_admitted():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a"), result("agent-b")
    evidence = pair.evidence(t, first, "agent-b", "challenge-the-output", target_output=second.output, target_verification=second.verification)
    assert pair.verify_evidence(evidence, task=t)
    assert pair.admit_consensus(t, first, second, evidence).valid


def test_admitted_evidence_cannot_be_replayed():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a"), result("agent-b")
    evidence = pair.evidence(t, first, "agent-b", "challenge", target_output=second.output, target_verification=second.verification)
    assert pair.admit_consensus(t, first, second, evidence).valid
    replay = pair.admit_consensus(t, first, second, evidence)
    assert not replay.valid and replay.reason == "evidence_replay_rejected"


def test_tampered_evidence_fails_closed():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY); second = result("agent-b")
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge", target_output=second.output, target_verification=second.verification)
    tampered = type(evidence)(**{**evidence.__dict__, "target_agent_id": "agent-c"})
    assert not pair.verify_evidence(tampered, task=t)


def test_target_output_tampering_fails_closed():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "one"), result("agent-b", "two")
    evidence = pair.evidence(t, first, second.agent_id, "challenge", target_output=second.output, target_verification=second.verification)
    forged = type(evidence)(**{**evidence.__dict__, "target_output_digest": pair._digest("three")})
    assert not pair.verify_evidence(forged, task=t)
    assert not pair.admit_consensus(t, first, second, forged).valid


def test_target_verification_tampering_fails_closed():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a"), result("agent-b")
    evidence = pair.evidence(t, first, second.agent_id, "challenge", target_output=second.output, target_verification=second.verification)
    forged = type(evidence)(**{**evidence.__dict__, "target_verification_digest": pair._digest(VerificationResult(True, "agent_result", "forged"))})
    assert not pair.verify_evidence(forged, task=t)
    assert not pair.admit_consensus(t, first, second, forged).valid


def test_cross_runtime_and_cross_execution_are_rejected():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY); second = result("agent-b")
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge", target_output=second.output, target_verification=second.verification)
    assert not PeerCollaboration("runtime-2", t.execution_id, seal_key=KEY).verify_evidence(evidence, task=t)
    assert not PeerCollaboration("runtime-1", "exec-2", seal_key=KEY).verify_evidence(evidence, task=t)


def test_same_agent_cannot_count_as_peer():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    with pytest.raises(ValueError, match="invalid_peer_identity"): pair.evidence(t, result("agent-a"), "agent-a", "challenge")


def test_unverified_result_cannot_enter_collaboration():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    bad = AgentResult("agent-a", t.task_id, "completed", "answer", VerificationResult(False, "agent_result", "bad"), t.execution_id)
    with pytest.raises(ValueError, match="unverified_source_result"): pair.evidence(t, bad, "agent-b", "challenge", target_output="answer")


def test_evidence_cannot_be_retargeted_to_different_task():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY); second = result("agent-b")
    evidence = pair.evidence(t, result("agent-a"), "agent-b", "challenge", target_output=second.output, target_verification=second.verification)
    other = TaskSpec("task-2", "analysis", "other", "input", execution_id=t.execution_id)
    assert not pair.verify_evidence(evidence, task=other)


def test_revision_evidence_requires_prior_admitted_chain_entry():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    revision = pair.evidence(t, result("agent-a", "revised"), "agent-b", "challenge", revision=1, previous_evidence_digest="0" * 64, target_output="revised", target_verification=result("agent-b").verification)
    assert not pair.verify_evidence(revision, task=t)


def test_revision_evidence_is_bound_to_the_initial_disagreement():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "one"), result("agent-b", "two")
    initial = pair.evidence(t, first, "agent-b", "resolve disagreement", target_output=second.output, target_verification=second.verification)
    assert not pair.admit_consensus(t, first, second, initial).valid
    initial_id = pair._evidence_id(initial)
    revised_first, revised_second = result("agent-a", "resolved"), result("agent-b", "resolved")
    revision = pair.evidence(t, revised_first, "agent-b", "re-evaluate after challenge", revision=1, previous_evidence_digest=initial_id, target_output=revised_second.output, target_verification=revised_second.verification)
    assert pair.verify_evidence(revision, task=t)
    assert pair.admit_consensus(t, revised_first, revised_second, revision).valid


def test_revision_cannot_follow_an_initial_consensus():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "same"), result("agent-b", "same")
    initial = pair.evidence(t, first, second.agent_id, "initial", target_output=second.output, target_verification=second.verification)
    assert pair.admit_consensus(t, first, second, initial).valid
    revised_second = result("agent-b", "changed")
    revision = pair.evidence(t, result("agent-a", "changed"), "agent-b", "invalid follow-up", revision=1, previous_evidence_digest=pair._evidence_id(initial), target_output=revised_second.output, target_verification=revised_second.verification)
    assert not pair.verify_evidence(revision, task=t)


def test_revision_cannot_skip_a_round():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "one"), result("agent-b", "two")
    initial = pair.evidence(t, first, second.agent_id, "initial", target_output=second.output, target_verification=second.verification)
    assert not pair.admit_consensus(t, first, second, initial).valid
    skipped = pair.evidence(t, result("agent-a", "three"), "agent-b", "skip", revision=2, previous_evidence_digest=pair._evidence_id(initial), target_output="three", target_verification=second.verification)
    assert not pair.verify_evidence(skipped, task=t)


def test_revision_cannot_switch_peer_pair():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "one"), result("agent-b", "two")
    initial = pair.evidence(t, first, second.agent_id, "initial", target_output=second.output, target_verification=second.verification)
    assert not pair.admit_consensus(t, first, second, initial).valid
    forged = pair.evidence(t, result("agent-a", "resolved"), "agent-c", "switch peer", revision=1, previous_evidence_digest=pair._evidence_id(initial), target_output="resolved", target_verification=second.verification)
    assert not pair.verify_evidence(forged, task=t)


def test_invalid_peer_result_does_not_poison_revision_chain():
    t = task(); pair = PeerCollaboration("runtime-1", t.execution_id, seal_key=KEY)
    first, second = result("agent-a", "one"), result("agent-b", "two")
    initial = pair.evidence(t, first, second.agent_id, "initial", target_output=second.output, target_verification=second.verification)
    bad_second = AgentResult("agent-b", t.task_id, "completed", "two", VerificationResult(False, "agent_result", "bad"), t.execution_id)
    rejected = pair.admit_consensus(t, first, bad_second, initial)
    assert not rejected.valid
    revision = pair.evidence(t, result("agent-a", "resolved"), "agent-b", "retry", revision=1, previous_evidence_digest=pair._evidence_id(initial), target_output="resolved", target_verification=second.verification)
    assert not pair.verify_evidence(revision, task=t)
