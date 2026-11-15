import pytest

from .matrix_inbox import DurableInbox, sign_message


KEY = b"noryx7-network-test-key-material-32-bytes"
KEY_ID = "node-a-key-v1"


def signed(message_id="m-1", payload=b"hello", *, sender="node-a", recipient="node-b", expiry=100):
    signature = sign_message(sender, recipient, message_id, KEY_ID, expiry, payload, KEY)
    return sender, recipient, message_id, KEY_ID, expiry, payload, signature


def inbox(tmp_path):
    return DurableInbox(str(tmp_path / "inbox.sqlite"), "node-b", {KEY_ID: KEY})


def test_authenticated_message_is_durable_and_idempotent(tmp_path):
    store = inbox(tmp_path)
    receipt = store.accept(*signed(), now=10)
    assert receipt.state == "PENDING"
    reopened = inbox(tmp_path)
    assert reopened.get("m-1") == receipt
    assert reopened.accept(*signed(), now=11) == receipt


def test_tampered_payload_signature_and_untrusted_key_are_rejected(tmp_path):
    store = inbox(tmp_path)
    sender, recipient, message_id, key_id, expiry, payload, signature = signed()
    with pytest.raises(PermissionError, match="message_authentication_failed"):
        store.accept(sender, recipient, message_id, key_id, expiry, b"tampered", signature, now=1)
    with pytest.raises(PermissionError, match="untrusted_message_key_id"):
        store.accept(sender, recipient, message_id, "unknown", expiry, payload, signature, now=1)


def test_recipient_binding_and_expiry_are_enforced(tmp_path):
    store = inbox(tmp_path)
    with pytest.raises(PermissionError, match="message_recipient_mismatch"):
        store.accept(*signed(recipient="node-c"), now=1)
    with pytest.raises(PermissionError, match="message_expired"):
        store.accept(*signed(expiry=5), now=5)


def test_message_id_cannot_be_reused_for_different_content(tmp_path):
    store = inbox(tmp_path)
    store.accept(*signed(), now=1)
    with pytest.raises(PermissionError, match="message_id_payload_conflict"):
        store.accept(*signed(payload=b"other"), now=1)


def test_delivery_is_persisted_and_idempotent(tmp_path):
    store = inbox(tmp_path)
    store.accept(*signed(), now=1)
    assert store.mark_delivered("m-1", now=2).state == "DELIVERED"
    assert inbox(tmp_path).mark_delivered("m-1", now=3).state == "DELIVERED"


def test_pending_message_expires_before_delivery(tmp_path):
    store = inbox(tmp_path)
    store.accept(*signed(expiry=10), now=1)
    assert store.mark_delivered("m-1", now=10).state == "EXPIRED"
    with pytest.raises(PermissionError, match="message_expired"):
        store.mark_delivered("m-1", now=11)


def test_payload_size_is_bounded(tmp_path):
    store = DurableInbox(str(tmp_path / "small.sqlite"), "node-b",
                         {KEY_ID: KEY}, max_payload_bytes=4)
    args = signed(payload=b"12345")
    with pytest.raises(ValueError, match="payload_invalid_or_too_large"):
        store.accept(*args, now=1)


def test_unknown_message_cannot_be_marked_delivered(tmp_path):
    with pytest.raises(KeyError, match="message_not_found"):
        inbox(tmp_path).mark_delivered("missing", now=1)
