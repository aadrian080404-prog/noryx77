import pytest

from core.key_lifecycle import KeyLifecycle, KeyState


def test_key_rotation_and_revocation_are_monotonic():
    lifecycle = KeyLifecycle()
    assert lifecycle.register("prod") == lifecycle.snapshot()[0]
    assert lifecycle.rotate("prod") == lifecycle.snapshot()[0]
    assert lifecycle.require_active("prod").version == 2
    assert lifecycle.retire("prod").state is KeyState.RETIRING
    with pytest.raises(PermissionError, match="key_not_active"):
        lifecycle.require_active("prod")
    lifecycle.revoke("prod")
    with pytest.raises(PermissionError, match="revoked_key_cannot_rotate"):
        lifecycle.rotate("prod")
