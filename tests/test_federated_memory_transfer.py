import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from core.federation.memory_transfer import (
    MemoryTransferRejected,
    SQLiteNonceRegistry,
    canonical_unsigned_envelope,
    ed25519_signature_verifier,
    open_memory_transfer,
    seal_memory_transfer,
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
        "ephemeral_public_key_b64": base64.b64encode(b"e" * 32).decode("ascii"),
        "aead_nonce_b64": base64.b64encode(b"n" * 12).decode("ascii"),
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
    ("expires_at", 150, "transfer_expired_or_invalid_ttl"),
    ("source_agent_id", "agent-a", "agent_scope_mapping_required"),
])
def test_rejects_scope_and_lifecycle_mismatches(field, value, error):
    envelope = make_envelope()
    envelope[field] = value
    with pytest.raises(MemoryTransferRejected, match=error):
        accept(envelope)


def test_rejects_modified_ciphertext_even_with_stale_digest():
    envelope = make_envelope()
    envelope["ciphertext_b64"] = base64.b64encode(b"tampered-ciphertext-long-enough").decode("ascii")
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



def test_ed25519_verification_and_durable_nonce_replay_protection(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    envelope = make_envelope()
    payload = canonical_unsigned_envelope(envelope)
    envelope["signature"] = base64.b64encode(private_key.sign(payload)).decode("ascii")
    verifier = ed25519_signature_verifier(
        lambda key_id: public_key if key_id == "issuer-key-a" else None
    )
    nonce_db = tmp_path / "transfer-nonces.db"
    registry = SQLiteNonceRegistry(str(nonce_db))
    try:
        accepted = validate_memory_transfer(
            envelope,
            expected_recipient_principal_id="principal-b",
            expected_recipient_key_id="recipient-key-b",
            verify_signature=verifier,
            reserve_nonce=registry.reserve,
            now=150,
        )
        assert accepted == base64.b64decode(envelope["ciphertext_b64"])
        with pytest.raises(MemoryTransferRejected, match="replay_or_nonce_store_unavailable"):
            validate_memory_transfer(
                envelope,
                expected_recipient_principal_id="principal-b",
                expected_recipient_key_id="recipient-key-b",
                verify_signature=verifier,
                reserve_nonce=registry.reserve,
                now=150,
            )
    finally:
        registry.close()

    # A fresh connection to the same database must still reject the nonce.
    restarted = SQLiteNonceRegistry(str(nonce_db))
    try:
        assert restarted.reserve("issuer-key-a", "unique-nonce", 200) is False
    finally:
        restarted.close()


def test_ed25519_verifier_rejects_unknown_keys_and_malformed_signatures():
    verifier = ed25519_signature_verifier(lambda _key_id: None)
    assert verifier("unknown-key", b"payload", "c2ln") is False

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    verifier = ed25519_signature_verifier(lambda _key_id: public_key)
    assert verifier("issuer-key-a", b"payload", "not-base64!") is False



def test_x25519_chacha20poly1305_round_trip_binds_identity_metadata(tmp_path):
    recipient_private = X25519PrivateKey.generate()
    recipient_private_raw = recipient_private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    recipient_public_raw = recipient_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    metadata = {
        "schema_version": 1,
        "transfer_id": "encrypted-transfer-1",
        "source_principal_id": "principal-a",
        "recipient_principal_id": "principal-b",
        "source_agent_id": "agent-a",
        "recipient_agent_id": "agent-a",
        "execution_id": "execution-1",
        "recipient_key_id": "recipient-key-b",
        "issued_at": 100,
        "expires_at": 200,
        "nonce": "encrypted-nonce-1",
        "issuer_key_id": "issuer-key-a",
    }
    envelope = seal_memory_transfer(
        b"private memory payload",
        metadata,
        recipient_public_raw,
    )
    issuer_private = Ed25519PrivateKey.generate()
    issuer_public = issuer_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    envelope["signature"] = base64.b64encode(
        issuer_private.sign(canonical_unsigned_envelope(envelope))
    ).decode("ascii")
    verifier = ed25519_signature_verifier(lambda _key_id: issuer_public)
    registry = SQLiteNonceRegistry(str(tmp_path / "encrypted-transfer-nonces.db"))
    try:
        plaintext = open_memory_transfer(
            envelope,
            recipient_private_key=recipient_private_raw,
            expected_recipient_principal_id="principal-b",
            expected_recipient_key_id="recipient-key-b",
            verify_signature=verifier,
            reserve_nonce=registry.reserve,
            now=150,
        )
        assert plaintext == b"private memory payload"
    finally:
        registry.close()


def test_encrypted_transfer_rejects_tampered_identity_binding(tmp_path):
    recipient_private = X25519PrivateKey.generate()
    recipient_private_raw = recipient_private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    recipient_public_raw = recipient_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    metadata = {
        "schema_version": 1, "transfer_id": "tamper-transfer",
        "source_principal_id": "principal-a", "recipient_principal_id": "principal-b",
        "source_agent_id": "", "recipient_agent_id": "",
        "execution_id": "execution-1", "recipient_key_id": "recipient-key-b",
        "issued_at": 100, "expires_at": 200, "nonce": "tamper-nonce",
        "issuer_key_id": "issuer-key-a",
    }
    envelope = seal_memory_transfer(b"private", metadata, recipient_public_raw)
    issuer_private = Ed25519PrivateKey.generate()
    issuer_public = issuer_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    envelope["signature"] = base64.b64encode(
        issuer_private.sign(canonical_unsigned_envelope(envelope))
    ).decode("ascii")
    envelope["recipient_principal_id"] = "attacker"
    registry = SQLiteNonceRegistry(str(tmp_path / "tamper-nonces.db"))
    try:
        with pytest.raises(MemoryTransferRejected, match="recipient_principal_mismatch"):
            open_memory_transfer(
                envelope,
                recipient_private_key=recipient_private_raw,
                expected_recipient_principal_id="principal-b",
                expected_recipient_key_id="recipient-key-b",
                verify_signature=ed25519_signature_verifier(lambda _key_id: issuer_public),
                reserve_nonce=registry.reserve,
                now=150,
            )
    finally:
        registry.close()



def test_encrypted_transfer_rejects_modified_ciphertext_even_when_resigned(tmp_path):
    recipient_private = X25519PrivateKey.generate()
    recipient_private_raw = recipient_private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    recipient_public_raw = recipient_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    metadata = {
        "schema_version": 1, "transfer_id": "aead-tamper-transfer",
        "source_principal_id": "principal-a", "recipient_principal_id": "principal-b",
        "source_agent_id": "", "recipient_agent_id": "",
        "execution_id": "execution-1", "recipient_key_id": "recipient-key-b",
        "issued_at": 100, "expires_at": 200, "nonce": "aead-tamper-nonce",
        "issuer_key_id": "issuer-key-a",
    }
    envelope = seal_memory_transfer(b"confidential payload", metadata, recipient_public_raw)
    ciphertext = bytearray(base64.b64decode(envelope["ciphertext_b64"]))
    ciphertext[0] ^= 0x01
    envelope["ciphertext_b64"] = base64.b64encode(ciphertext).decode("ascii")
    envelope["ciphertext_sha256"] = hashlib.sha256(ciphertext).hexdigest()

    issuer_private = Ed25519PrivateKey.generate()
    issuer_public = issuer_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    envelope["signature"] = base64.b64encode(
        issuer_private.sign(canonical_unsigned_envelope(envelope))
    ).decode("ascii")
    registry = SQLiteNonceRegistry(str(tmp_path / "aead-tamper-nonces.db"))
    try:
        with pytest.raises(MemoryTransferRejected, match="memory_decryption_failed"):
            open_memory_transfer(
                envelope,
                recipient_private_key=recipient_private_raw,
                expected_recipient_principal_id="principal-b",
                expected_recipient_key_id="recipient-key-b",
                verify_signature=ed25519_signature_verifier(lambda _key_id: issuer_public),
                reserve_nonce=registry.reserve,
                now=150,
            )
    finally:
        registry.close()
