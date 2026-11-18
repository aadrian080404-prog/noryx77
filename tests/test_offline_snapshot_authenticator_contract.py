import pytest

from core.offline import OfflineRuntime


class _Recovery:
    def snapshot(self):
        return "normal", 1

    def run_if_normal(self, operation, *, expected_epoch=None):
        return operation()


class _Policy:
    def authorize(self, *, principal_id, operation, offline):
        return True


class _Verifier:
    def verify(self, result):
        return True


class _Cipher:
    def encrypt(self, plaintext, *, aad):
        return b"encrypted:" + plaintext

    def decrypt(self, ciphertext, *, aad):
        return ciphertext.removeprefix(b"encrypted:")


def test_offline_runtime_rejects_bare_callable_snapshot_authenticator():
    with pytest.raises(TypeError, match="offline_snapshot_authenticator_and_clock_required"):
        OfflineRuntime(
            recovery=_Recovery(),
            policy=_Policy(),
            verifier=_Verifier(),
            cipher=_Cipher(),
            clock=lambda: 100,
            snapshot_authenticator=lambda snapshot: True,
        )
