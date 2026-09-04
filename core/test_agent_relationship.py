from __future__ import annotations

import hashlib
import hmac

import pytest

from .agent_relationship import AgentRelationshipStore, CollaborationEvidence


def test_relationship_is_bound_to_runtime_and_pair():
    store = AgentRelationshipStore("runtime-a", "pair-a", b"k" * 32)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    assert event.runtime_id == "runtime-a"
    assert event.pair_id == "pair-a"
    assert store.relationship_facts()["verified_challenges"] == 1


def test_tampering_is_quarantined():
    store = AgentRelationshipStore("runtime-a", "pair-a", b"k" * 32)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    forged = CollaborationEvidence(event.runtime_id, event.pair_id, event.execution_id, event.interaction_id,
                                    event.source_agent_id, event.target_agent_id, event.event_type,
                                    "0" * 64, event.previous_digest, event.seal)
    assert not store.admit(forged)
    assert len(store.quarantined()) == 1


def test_cross_pair_event_is_rejected():
    source = AgentRelationshipStore("runtime-a", "pair-a", b"k" * 32)
    event = source.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="successful_correction", evidence={"ok": True})
    other = AgentRelationshipStore("runtime-a", "pair-b", b"k" * 32)
    assert not other.admit(event)


def test_chain_break_is_rejected():
    store = AgentRelationshipStore("runtime-a", "pair-a", b"k" * 32)
    first = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    forged = CollaborationEvidence(store.runtime_id, store.pair_id, "exec", "i2", "a", "b", "successful_correction", "1" * 64, "0" * 64, "1" * 64)
    assert not store.admit(forged)
    assert store.snapshot() == (first,)


def test_replay_is_rejected():
    store = AgentRelationshipStore("runtime-a", "pair-a", b"k" * 32)
    event = store.record(execution_id="exec", interaction_id="i1", source_agent_id="a", target_agent_id="b", event_type="verified_challenge", evidence={"ok": True})
    assert not store.admit(event)


def test_short_key_is_rejected():
    with pytest.raises(ValueError):
        AgentRelationshipStore("runtime-a", "pair-a", b"short")
