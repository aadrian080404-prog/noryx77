import pytest

from .journal_integrity import (
    AnchorSnapshot, InMemoryMonotonicAnchor, JournalAuthenticator,
    ZERO_MAC, verify_anchored_head,
)


def test_authenticated_chain_and_external_anchor():
    auth = JournalAuthenticator(b"k" * 32, key_id="kms-key-v1")
    payloads = (b"first-state", b"second-state")
    first = auth.create(1, ZERO_MAC, payloads[0])
    second = auth.create(2, first.mac, payloads[1])
    entries = ((first, payloads[0]), (second, payloads[1]))
    anchor = InMemoryMonotonicAnchor()
    assert anchor.compare_and_swap(AnchorSnapshot(0, ZERO_MAC), AnchorSnapshot(1, first.mac))
    assert anchor.compare_and_swap(AnchorSnapshot(1, first.mac), AnchorSnapshot(2, second.mac))
    assert verify_anchored_head(auth, entries, anchor) == AnchorSnapshot(2, second.mac)


def test_chain_detects_payload_tampering():
    auth = JournalAuthenticator(b"k" * 32, key_id="kms-key-v1")
    proof = auth.create(1, ZERO_MAC, b"original")
    with pytest.raises(ValueError, match="journal_record_authentication_failure"):
        auth.verify_chain(((proof, b"changed"),))


def test_chain_detects_reordering_and_missing_records():
    auth = JournalAuthenticator(b"k" * 32, key_id="kms-key-v1")
    one = auth.create(1, ZERO_MAC, b"one")
    two = auth.create(2, one.mac, b"two")
    with pytest.raises(ValueError, match="journal_chain_discontinuity"):
        auth.verify_chain(((two, b"two"),))
    # A chain verifier cannot infer an omitted tail from the chain alone.
    assert auth.verify_chain(((one, b"one"),)).sequence == 1
    anchor = InMemoryMonotonicAnchor()
    assert anchor.compare_and_swap(AnchorSnapshot(0, ZERO_MAC), AnchorSnapshot(1, one.mac))
    assert anchor.compare_and_swap(AnchorSnapshot(1, one.mac), AnchorSnapshot(2, two.mac))
    with pytest.raises(ValueError, match="journal_anchor_mismatch"):
        verify_anchored_head(auth, ((one, b"one"),), anchor)


def test_external_anchor_detects_rollback():
    auth = JournalAuthenticator(b"k" * 32, key_id="kms-key-v1")
    one = auth.create(1, ZERO_MAC, b"one")
    two = auth.create(2, one.mac, b"two")
    anchor = InMemoryMonotonicAnchor()
    assert anchor.compare_and_swap(AnchorSnapshot(0, ZERO_MAC), AnchorSnapshot(1, one.mac))
    assert anchor.compare_and_swap(AnchorSnapshot(1, one.mac), AnchorSnapshot(2, two.mac))
    with pytest.raises(ValueError, match="journal_anchor_mismatch"):
        verify_anchored_head(auth, ((one, b"one"),), anchor)


def test_invalid_keys_and_sequences_fail_closed():
    with pytest.raises(ValueError):
        JournalAuthenticator(b"short", key_id="key")
    auth = JournalAuthenticator(b"k" * 32, key_id="key")
    with pytest.raises(ValueError):
        auth.create(True, ZERO_MAC, b"x")
