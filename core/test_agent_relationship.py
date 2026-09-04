from __future__ import annotations

import pytest

from .agent_relationship import AgentRelationshipStore, CollaborationEvidence


KEY = b"k" * 32


def test_relationship_is_bound_to_runtime_and_pair():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    assert event.runtime_id == "runtime-a"
    assert event.pair_id == "pair-a"
    assert store.relationship_facts()["verified_challenges"] == 1


def test_evidence_payload_digest_is_recomputed():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    payload = {"ok": True, "score": 1}
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence=payload)
    assert store.verify_evidence_payload(event, payload)
    assert not store.verify_evidence_payload(event, {"ok": False, "score": 1})


def test_tampering_is_quarantined():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    forged = CollaborationEvidence(event.runtime_id, event.pair_id, event.execution_id, event.interaction_id,
                                    event.source_agent_id, event.target_agent_id, event.event_type,
                                    "0" * 64, event.previous_digest, event.seal)
    assert not store.admit(forged)
    assert len(store.quarantined()) == 1


def test_cross_pair_event_is_rejected():
    source = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    event = source.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="successful_correction", evidence={"ok": True})
    other = AgentRelationshipStore("runtime-a", "pair-b", KEY)
    assert not other.admit(event)
    assert len(other.quarantined()) == 1


def test_chain_break_is_rejected():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    first = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    forged = CollaborationEvidence(store.runtime_id, store.pair_id, "exec", "i2", "a", "b", "successful_correction", "1" * 64, "0" * 64, "1" * 64)
    assert not store.admit(forged)
    assert store.snapshot() == (first,)


def test_replay_is_rejected():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    assert not store.admit(event)


def test_same_agent_and_invalid_identity_are_rejected():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY)
    with pytest.raises(ValueError, match="relationship peers must be distinct"):
        store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="a", event_type="verified_challenge", evidence={})
    with pytest.raises(ValueError, match="invalid relationship identity"):
        store.record(execution_id="", interaction_id="i2", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={})


def test_event_limit_is_fail_closed():
    store = AgentRelationshipStore("runtime-a", "pair-a", KEY, max_events=1)
    store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    with pytest.raises(RuntimeError, match="relationship event limit exceeded"):
        store.record(execution_id="exec", interaction_id="i2", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})


def test_short_key_is_rejected():
    with pytest.raises(ValueError):
        AgentRelationshipStore("runtime-a", "pair-a", b"short")
