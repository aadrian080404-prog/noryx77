from __future__ import annotations

import pytest

from core.key_lifecycle import KeyLifecycle, KeyState


def test_key_lifecycle_cannot_reactivate_retiring_key():
    lifecycle = KeyLifecycle()
    lifecycle.register("prod")

    retired = lifecycle.retire("prod")
    assert retired.state is KeyState.RETIRING

    with pytest.raises(
        PermissionError,
        match="retiring_key_cannot_reactivate",
    ):
        lifecycle.rotate("prod")

    assert lifecycle.snapshot()[0] == retired
    assert lifecycle.snapshot()[0].state is KeyState.RETIRING


def test_key_lifecycle_remains_monotonic_after_retirement():
    lifecycle = KeyLifecycle()
    lifecycle.register("prod")

    first = lifecycle.rotate("prod")
    assert first.version == 2
    assert first.state is KeyState.ACTIVE

    retired = lifecycle.retire("prod")
    assert retired.version == 2
    assert retired.state is KeyState.RETIRING

    with pytest.raises(PermissionError, match="key_not_active"):
        lifecycle.require_active("prod")

    with pytest.raises(
        PermissionError,
        match="retiring_key_cannot_reactivate",
    ):
        lifecycle.rotate("prod")

    revoked = lifecycle.revoke("prod")
    assert revoked.version == 2
    assert revoked.state is KeyState.REVOKED

    with pytest.raises(
        PermissionError,
        match="revoked_key_cannot_rotate",
    ):
        lifecycle.rotate("prod")
