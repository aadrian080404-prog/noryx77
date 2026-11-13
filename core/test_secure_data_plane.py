import os
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .secure_data_plane import SecureDataPlane


class __TestKMS:
    """Test-only envelope-key adapter; production keys remain outside NORYX7."""

    def __init__(self):
        self._wrapping_key = os.urandom(32)

    @staticmethod
    def _context(tenant_id, purpose):
        return f"noryx7-test-kms|{tenant_id}|{purpose}".encode()

    def generate_data_key(self, *, tenant_id, purpose):
        data_key = os.urandom(32)
        nonce = os.urandom(12)
        wrapped = nonce + AESGCM(self._wrapping_key).encrypt(
            nonce, data_key, self._context(tenant_id, purpose)
        )
        return data_key, wrapped, "test-kms-key-version-1"

    def unwrap_data_key(self, *, wrapped_key, key_id, tenant_id, purpose):
        if key_id != "test-kms-key-version-1" or len(wrapped_key) < 28:
            raise PermissionError("invalid_wrapped_key")
        nonce, ciphertext = wrapped_key[:12], wrapped_key[12:]
        return AESGCM(self._wrapping_key).decrypt(
            nonce, ciphertext, self._context(tenant_id, purpose)
        )


def test_per_record_envelope_encryption_round_trip_and_randomization():
    plane = SecureDataPlane(__TestKMS())
    plaintext = b"highly confidential customer record"
    first = plane.encrypt(
        plaintext, tenant_id="tenant-a", record_id="record-1",
        purpose="banking-ledger", classification="restricted",
    )
    second = plane.encrypt(
        plaintext, tenant_id="tenant-a", record_id="record-1",
        purpose="banking-ledger", classification="restricted",
    )

    assert first.ciphertext != plaintext
    assert first.nonce != second.nonce
    assert first.wrapped_key != second.wrapped_key
    assert plane.decrypt(
        first, tenant_id="tenant-a", record_id="record-1",
        purpose="banking-ledger",
    ) == plaintext


def test_ciphertext_cannot_be_moved_between_tenants_records_or_purposes():
    plane = SecureDataPlane(_TestKMS())
    record = plane.encrypt(
        b"secret", tenant_id="tenant-a", record_id="record-1",
        purpose="payments",
    )
    for context in (
        ("tenant-b", "record-1", "payments"),
        ("tenant-a", "record-2", "payments"),
        ("tenant-a", "record-1", "market-data"),
    ):
        with pytest.raises(PermissionError, match="context_mismatch"):
            plane.decrypt(
                record, tenant_id=context[0], record_id=context[1],
                purpose=context[2],
            )


def test_ciphertext_and_authenticated_metadata_tampering_are_rejected():
    plane = SecureDataPlane(_TestKMS())
    record = plane.encrypt(
        b"secret", tenant_id="tenant-a", record_id="record-1",
        purpose="identity",
    )
    changed = bytearray(record.ciphertext)
    changed[0] ^= 1
    with pytest.raises(PermissionError, match="ciphertext_authentication_failed"):
        plane.decrypt(
            replace(record, ciphertext=bytes(changed)),
            tenant_id="tenant-a", record_id="record-1", purpose="identity",
        )
    with pytest.raises(PermissionError, match="metadata_tampered"):
        plane.decrypt(
            replace(record, classification="public"),
            tenant_id="tenant-a", record_id="record-1", purpose="identity",
        )


def test_invalid_records_and_payload_limits_fail_closed():
    plane = SecureDataPlane(_TestKMS(), max_payload_bytes=8)
    with pytest.raises(ValueError, match="payload_size_exceeded"):
        plane.encrypt(b"123456789", tenant_id="t", record_id="r", purpose="p")
    with pytest.raises(ValueError, match="invalid_data_classification"):
        plane.encrypt(b"x", tenant_id="t", record_id="r", purpose="p", classification="unknown")
    with pytest.raises(ValueError, match="invalid_encrypted_record"):
        plane.decrypt(object(), tenant_id="t", record_id="r", purpose="p")
    malformed = plane.encrypt(b"x", tenant_id="t", record_id="r", purpose="p")
    assert not replace(malformed, version=True).is_well_formed()
    assert not replace(malformed, classification=[]).is_well_formed()


def test_kms_failure_never_returns_plaintext_or_falls_back_to_local_keys():
    class UnavailableKMS:
        def generate_data_key(self, **_kwargs):
            raise RuntimeError("kms unavailable")

        def unwrap_data_key(self, **_kwargs):
            raise RuntimeError("kms unavailable")

    plane = SecureDataPlane(UnavailableKMS())
    with pytest.raises(PermissionError, match="key_generation_unavailable"):
        plane.encrypt(b"secret", tenant_id="t", record_id="r", purpose="p")
