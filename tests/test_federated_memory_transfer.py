import base64
import hashlib
import json

import pytest

from core.federation.memory_transfer import (
    MemoryTransferRejected,
    canonical_unsigned_envelope,
    validate_memory_transfer,
)


def make_envelope():
    ciphertext = b"opaque-encrypted-memory"
    return {
        "schema_version": 1,
        "transfer_id": "transfer-1",
        "source_principal_id": "principal-a",
        "recipient_principal_id": "principal-b",
        "source_agent_id": "",
        "recipient_agent_id": "",
        "execution_id": "execution-1",
        "recipient_key_id": "recipient-key-b",
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "issued_at": 100,
        "expires_at": 200,
        "nonce": "unique-nonce",
        "issuer_key_id": "issuer-key-a",
        "signature": "signature",
    }


def accept(envelope, *, reserve=None, verify=True, **overrides):
    calls = []
    return validate_memory_transfer(
        envelope,
        expected_recipient_principal_id="principal-b",
        expected_recipient_key_id="recipient-key-b",
        verify_signature=lambda key, payload, signature: verify,
        reserve_nonce=reserve or (lambda key, nonce, expiry: calls.append((key, nonce, expiry)) or True),
        now=150,
        **overrides,
    )


def test_accepts_only_opaque_ciphertext_after_signature_and_nonce_reservation():
    envelope = make_envelope()
    ciphertext = accept(envelope)
    assert ciphertext == base64.b64decode(envelope["ciphertext_b64"])


@pytest.mark.parametrize("field,value,error", [
    ("recipient_principal_id", "attacker", "recipient_principal_mismatch"),
    ("recipient_key_id", "wrong-key", "recipient_key_mismatch"),
    ("expires_at", 151, "transfer_expired_or_invalid_ttl"),
    ("source_agent_id", "agent-a", "agent_scope_mapping_required"),
])
def test_rejects_scope_and_lifecycle_mismatches(field, value, error):
    envelope = make_envelope()
    envelope[field] = value
    with pytest.raises(MemoryTransferRejected, match=error):
        accept(envelope)


def test_rejects_modified_ciphertext_even_with_stale_digest():
    envelope = make_envelope()
    envelope["ciphertext_b64"] = base64.b64encode(b"tampered").decode("ascii")
    with pytest.raises(MemoryTransferRejected, match="ciphertext_digest_mismatch"):
        accept(envelope)


def test_rejects_invalid_signature_before_nonce_reservation():
    envelope = make_envelope()
    reservations = []
    with pytest.raises(MemoryTransferRejected, match="signature_verification_failed"):
        validate_memory_transfer(
            envelope,
            expected_recipient_principal_id="principal-b",
            expected_recipient_key_id="recipient-key-b",
            verify_signature=lambda *_: False,
            reserve_nonce=lambda *args: reservations.append(args) or True,
            now=150,
        )
    assert reservations == []


def test_rejects_replay_or_unavailable_durable_nonce_store():
    with pytest.raises(MemoryTransferRejected, match="replay_or_nonce_store_unavailable"):
        accept(make_envelope(), reserve=lambda *_: False)


def test_signature_canonicalization_is_order_independent_and_excludes_signature():
    envelope = make_envelope()
    reordered = dict(reversed(list(envelope.items())))
    assert canonical_unsigned_envelope(envelope) == canonical_unsigned_envelope(reordered)
    reordered["signature"] = "different"
    assert canonical_unsigned_envelope(envelope) == canonical_unsigned_envelope(reordered)


def test_rejects_unknown_or_missing_fields():
    envelope = make_envelope()
    envelope["plaintext"] = "must-never-be-carried"
    with pytest.raises(MemoryTransferRejected, match="invalid_envelope_fields"):
        accept(envelope)
