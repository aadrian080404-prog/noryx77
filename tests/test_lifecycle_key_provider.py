import pytest

from core.crypto import AuthenticatedCipher
from core.durable_key_lifecycle import DurableKeyLifecycle
from core.key_lifecycle import ExternalKeyBoundary, KeyLifecycle, KeyState
from core.lifecycle_key_provider import LifecycleBoundKeyProvider


class TestExternalKMS(ExternalKeyBoundary):
    def __init__(self):
        self.calls = []

    def get_key(self, key_id, version):
        self.calls.append((key_id, version))
        return bytes([version]) * 32


def test_lifecycle_bound_provider_fetches_active_version_only(tmp_path):
    lifecycle = DurableKeyLifecycle(
        str(tmp_path / "keys.sqlite"),
        integrity_key=b"lifecycle-provider-test-integrity-key-at-least-32",
        key_id="metadata-v1",
    )
    lifecycle.register("memory-key")
    kms = TestExternalKMS()
    provider = LifecycleBoundKeyProvider(kms, lifecycle)
    cipher = AuthenticatedCipher(provider)

    envelope = cipher.encrypt(b"private memory", key_id="memory-key")
    assert cipher.decrypt(envelope) == b"private memory"
    assert kms.calls == [("memory-key", 1), ("memory-key", 1)]

    lifecycle.rotate("memory-key")
    rotated = cipher.encrypt(b"rotated", key_id="memory-key")
    assert cipher.decrypt(rotated) == b"rotated"
    assert kms.calls[-2:] == [("memory-key", 2), ("memory-key", 2)]
    lifecycle.close()


def test_lifecycle_bound_provider_rejects_retired_and_revoked_keys(tmp_path):
    lifecycle = DurableKeyLifecycle(
        str(tmp_path / "keys.sqlite"),
        integrity_key=b"lifecycle-provider-test-integrity-key-at-least-32",
        key_id="metadata-v1",
    )
    lifecycle.register("signing-key")
    provider = LifecycleBoundKeyProvider(TestExternalKMS(), lifecycle)
    lifecycle.retire("signing-key")
    with pytest.raises(PermissionError, match="key_not_active"):
        provider.get_key("signing-key")
    lifecycle.revoke("signing-key")
    with pytest.raises(PermissionError, match="key_not_active"):
        provider.get_key("signing-key")
    lifecycle.close()


def test_lifecycle_bound_provider_requires_durable_metadata(tmp_path):
    with pytest.raises(ValueError, match="durable_key_lifecycle_required"):
        LifecycleBoundKeyProvider(TestExternalKMS(), KeyLifecycle())


def test_lifecycle_bound_provider_rejects_closed_lifecycle(tmp_path):
    lifecycle = DurableKeyLifecycle(
        str(tmp_path / "keys.sqlite"),
        integrity_key=b"lifecycle-provider-test-integrity-key-at-least-32",
        key_id="metadata-v1",
    )
    lifecycle.register("key")
    provider = LifecycleBoundKeyProvider(TestExternalKMS(), lifecycle)
    lifecycle.close()
    with pytest.raises(RuntimeError, match="unavailable"):
        provider.get_key("key")
