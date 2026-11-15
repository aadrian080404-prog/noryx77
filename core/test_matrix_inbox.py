import pytest

from .matrix_inbox import DurableInbox, sign_message
from .matrix_key_policy import DurableKeyPolicyRegistry
from .matrix_key_policy import DurableKeyPolicyRegistry


KEY = b"noryx7-network-test-key-material-32-bytes"
KEY_ID = "node-a-key-v1"


def signed(message_id="m-1", payload=b"hello", *, sender="node-a", recipient="node-b", expiry=100):
    signature = sign_message(sender, recipient, message_id, KEY_ID, expiry, payload, KEY)
    return sender, recipient, message_id, KEY_ID, expiry, payload, signature


def inbox(tmp_path):
    return DurableInbox(str(tmp_path / "inbox.sqlite"), "node-b", {KEY_ID: KEY}, trusted_senders={KEY_ID: "node-a"})


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
                         {KEY_ID: KEY}, trusted_senders={KEY_ID: "node-a"}, max_payload_bytes=4)
    args = signed(payload=b"12345")
    with pytest.raises(ValueError, match="payload_invalid_or_too_large"):
        store.accept(*args, now=1)


def test_unknown_message_cannot_be_marked_delivered(tmp_path):
    with pytest.raises(KeyError, match="message_not_found"):
        inbox(tmp_path).mark_delivered("missing", now=1)



def test_key_id_is_bound_to_its_authorized_sender(tmp_path):
    store = inbox(tmp_path)
    args = signed(sender="node-impersonated")
    with pytest.raises(PermissionError, match="message_sender_key_binding_mismatch"):
        store.accept(*args, now=1)


def test_pending_payload_can_be_read_and_retried_until_acknowledged(tmp_path):
    store = inbox(tmp_path)
    store.accept(*signed(payload=b"work-item"), now=1)
    first = store.read_pending("m-1", now=2)
    second = store.read_pending("m-1", now=3)
    assert first == second
    assert first[1] == b"work-item"
    assert store.mark_delivered("m-1", now=4).state == "DELIVERED"
    assert store.read_pending("m-1", now=5) is None


def test_pending_payload_read_expires_atomically(tmp_path):
    store = inbox(tmp_path)
    store.accept(*signed(expiry=10), now=1)
    assert store.read_pending("m-1", now=10) is None
    assert store.get("m-1").state == "EXPIRED"


def test_inbox_requires_complete_sender_key_bindings(tmp_path):
    with pytest.raises(ValueError, match="trusted_sender_binding_required"):
        DurableInbox(str(tmp_path / "bad.sqlite"), "node-b", {KEY_ID: KEY},
                     trusted_senders={})



def test_inbox_trusted_key_resolver_rejects_revocation(tmp_path):
    policy = DurableKeyPolicyRegistry(
        str(tmp_path / "key-policy.sqlite"),
        authorize=lambda *_args: True,
        key_resolver=lambda _key_id: KEY,
    )
    policy.register(KEY_ID, "owner-a", "NETWORK_HMAC", 1)
    def resolve(key_id, sender_id):
        if sender_id != "node-a":
            raise PermissionError("sender_not_authorized")
        return policy.resolve(key_id, "owner-a", "NETWORK_HMAC")
    store = DurableInbox(
        str(tmp_path / "policy-inbox.sqlite"), "node-b", {},
        trusted_senders={KEY_ID: "node-a"}, trusted_key_resolver=resolve,
    )
    store.accept(*signed(message_id="before-revoke"), now=1)
    policy.revoke(KEY_ID, "owner-a", generation=2)
    with pytest.raises(PermissionError, match="key_revoked"):
        store.accept(*signed(message_id="after-revoke"), now=2)



def test_inbox_resolves_key_policy_dynamically_and_rejects_revoked_key(tmp_path):
    registry = DurableKeyPolicyRegistry(
        str(tmp_path / "key-policy.sqlite"),
        authorize=lambda *_args: True,
        key_resolver=lambda _key_id: KEY,
    )
    registry.register(KEY_ID, "owner-a", "NETWORK_HMAC", 1)
    store = DurableInbox(
        str(tmp_path / "policy-inbox.sqlite"),
        "node-b",
        trusted_senders={KEY_ID: "node-a"},
        key_resolver=lambda key_id: registry.resolve(
            key_id, "owner-a", "NETWORK_HMAC"
        ),
    )
    args = signed(message_id="policy-message", payload=b"before-revoke")
    assert store.accept(*args, now=1).state == "PENDING"

    registry.revoke(KEY_ID, "owner-a", generation=2)
    # Key policy is checked before duplicate/idempotency handling, so a replay
    # cannot continue to authenticate after the key has been revoked.
    with pytest.raises(PermissionError, match="key_revoked"):
        store.accept(*args, now=2)

    # Previously accepted but not yet delivered payloads are also blocked.
    with pytest.raises(PermissionError, match="key_revoked"):
        store.read_pending("policy-message", now=2)


def test_inbox_key_resolver_fails_closed_on_provider_error(tmp_path):
    def unavailable(_key_id):
        raise RuntimeError("kms unavailable")

    store = DurableInbox(
        str(tmp_path / "resolver-inbox.sqlite"),
        "node-b",
        trusted_senders={KEY_ID: "node-a"},
        key_resolver=unavailable,
    )
    with pytest.raises(PermissionError, match="message_key_resolution_failed"):
        store.accept(*signed(), now=1)
