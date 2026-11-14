import pytest

from core.crypto import AuthenticatedCipher, LifecycleBoundKeyProvider
from core.key_lifecycle import SQLiteKeyLifecycle, KeyState


class FakeKMS:
    def __init__(self):
        self.calls = []
        self.keys = {("data", 1): b"a" * 32, ("data", 2): b"b" * 32}

    def get_key(self, key_id, version):
        self.calls.append((key_id, version))
        return self.keys[(key_id, version)]


def test_cipher_uses_active_persisted_key_version(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.register("data")
    kms = FakeKMS()
    cipher = AuthenticatedCipher(LifecycleBoundKeyProvider(lifecycle, kms))
    envelope = cipher.encrypt(b"secret", key_id="data")
    assert cipher.decrypt(envelope) == b"secret"
    assert kms.calls == [("data", 1), ("data", 1)]
    lifecycle.close()


def test_revoked_and_retiring_keys_are_denied_before_kms_fetch(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.register("data")
    kms = FakeKMS()
    provider = LifecycleBoundKeyProvider(lifecycle, kms)
    lifecycle.retire("data")
    with pytest.raises(PermissionError, match="key_not_active"):
        provider.get_key("data")
    lifecycle.revoke("data")
    with pytest.raises(PermissionError, match="key_not_active"):
        provider.get_key("data")
    assert kms.calls == []
    lifecycle.close()


def test_rotation_selects_new_external_key_version(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.register("data")
    kms = FakeKMS()
    provider = LifecycleBoundKeyProvider(lifecycle, kms)
    assert provider.get_key("data") == b"a" * 32
    lifecycle.rotate("data")
    assert provider.get_key("data") == b"b" * 32
    assert kms.calls == [("data", 1), ("data", 2)]
    lifecycle.close()


def test_rotation_during_fetch_invalidates_retrieved_key(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.register("data")

    class RacingKMS(FakeKMS):
        def get_key(self, key_id, version):
            result = super().get_key(key_id, version)
            lifecycle.rotate(key_id)
            return result

    provider = LifecycleBoundKeyProvider(lifecycle, RacingKMS())
    with pytest.raises(PermissionError, match="changed_during"):
        provider.get_key("data")
    lifecycle.close()


def test_external_kms_invalid_key_material_is_rejected(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    lifecycle.register("data")
    class BadKMS:
        def get_key(self, key_id, version):
            return b"short"
    with pytest.raises(ValueError, match="aes256"):
        LifecycleBoundKeyProvider(lifecycle, BadKMS()).get_key("data")
    lifecycle.close()
