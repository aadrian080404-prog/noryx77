import concurrent.futures

import pytest

from core.key_lifecycle import KeyState, SQLiteKeyLifecycle


def test_lifecycle_survives_restart_and_preserves_revocation(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    lifecycle = SQLiteKeyLifecycle(path)
    lifecycle.register("signing-key")
    assert lifecycle.rotate("signing-key").version == 2
    assert lifecycle.retire("signing-key").state is KeyState.RETIRING
    lifecycle.revoke("signing-key")
    lifecycle.close()

    reopened = SQLiteKeyLifecycle(path)
    record = reopened.snapshot()[0]
    assert record.key_id == "signing-key"
    assert record.version == 2
    assert record.state is KeyState.REVOKED
    with pytest.raises(PermissionError, match="key_not_active"):
        reopened.require_active("signing-key")
    with pytest.raises(PermissionError, match="revoked_key_cannot_rotate"):
        reopened.rotate("signing-key")
    reopened.close()


def test_duplicate_registration_and_invalid_versions_fail_closed(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    with pytest.raises(ValueError, match="invalid_key_version"):
        lifecycle.register("key", version=True)
    lifecycle.register("key")
    with pytest.raises(ValueError, match="key_id_already_registered"):
        lifecycle.register("key")
    lifecycle.close()


def test_unknown_key_and_closed_store_are_rejected(tmp_path):
    lifecycle = SQLiteKeyLifecycle(str(tmp_path / "keys.sqlite"))
    with pytest.raises(KeyError, match="unknown_key_id"):
        lifecycle.require_active("missing")
    lifecycle.close()
    with pytest.raises(RuntimeError, match="key_lifecycle_closed"):
        lifecycle.snapshot()


def test_concurrent_rotations_are_serialized_across_connections(tmp_path):
    path = str(tmp_path / "keys.sqlite")
    first = SQLiteKeyLifecycle(path)
    second = SQLiteKeyLifecycle(path)
    first.register("key")

    def rotate(store):
        return store.rotate("key").version

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        versions = list(pool.map(rotate, (first, second)))

    assert sorted(versions) == [2, 3]
    assert first.require_active("key").version == 3
    first.close()
    second.close()
