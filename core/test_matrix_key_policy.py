import pytest

from .matrix_key_policy import DurableKeyPolicyRegistry


KEY = b"external-kms-test-material-32-bytes"


def make_registry(tmp_path, *, allowed=True, material=KEY):
    return DurableKeyPolicyRegistry(
        str(tmp_path / "key-policy.sqlite"),
        authorize=lambda *_args: allowed,
        key_resolver=lambda _key_id: material,
    )


def test_key_policy_persists_and_resolves_only_matching_owner_purpose(tmp_path):
    store = make_registry(tmp_path)
    record = store.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    assert record.state == "ACTIVE"
    reopened = make_registry(tmp_path)
    assert reopened.get("k-1") == record
    assert reopened.resolve("k-1", "owner-a", "OBJECT_AUTH") == KEY
    with pytest.raises(PermissionError, match="key_scope_mismatch"):
        reopened.resolve("k-1", "owner-b", "OBJECT_AUTH")
    with pytest.raises(PermissionError, match="key_scope_mismatch"):
        reopened.resolve("k-1", "owner-a", "NETWORK_HMAC")


def test_key_rotation_requires_monotonic_generation(tmp_path):
    store = make_registry(tmp_path)
    store.register("k-1", "owner-a", "NETWORK_HMAC", 1)
    store.register("k-2", "owner-a", "NETWORK_HMAC", 2)
    with pytest.raises(PermissionError, match="key_generation_not_monotonic"):
        store.register("k-3", "owner-a", "NETWORK_HMAC", 2)


def test_revoked_key_is_not_resolvable_after_restart(tmp_path):
    store = make_registry(tmp_path)
    store.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    revoked = store.revoke("k-1", "owner-a", generation=2)
    assert revoked.state == "REVOKED"
    reopened = make_registry(tmp_path)
    with pytest.raises(PermissionError, match="key_revoked"):
        reopened.resolve("k-1", "owner-a", "OBJECT_AUTH")


def test_key_identifier_cannot_be_rebound(tmp_path):
    store = make_registry(tmp_path)
    store.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    with pytest.raises(PermissionError, match="key_id_already_bound"):
        store.register("k-1", "owner-b", "OBJECT_AUTH", 1)


def test_registration_revocation_and_resolution_fail_closed(tmp_path):
    denied = make_registry(tmp_path, allowed=False)
    with pytest.raises(PermissionError, match="key_registration_not_authorized"):
        denied.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    allowed = make_registry(tmp_path)
    allowed.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    with pytest.raises(PermissionError, match="key_resolution_not_authorized"):
        denied.resolve("k-1", "owner-a", "OBJECT_AUTH")
    with pytest.raises(PermissionError, match="key_revocation_not_authorized"):
        denied.revoke("k-1", "owner-a", generation=2)


def test_registry_rejects_unsupported_purpose_and_invalid_provider_material(tmp_path):
    with pytest.raises(ValueError, match="unsupported_key_purpose"):
        make_registry(tmp_path).register("k", "owner", "ANYTHING", 1)
    invalid = make_registry(tmp_path, material=b"short")
    invalid.register("k-1", "owner-a", "OBJECT_AUTH", 1)
    with pytest.raises(PermissionError, match="key_provider_returned_invalid_material"):
        invalid.resolve("k-1", "owner-a", "OBJECT_AUTH")


def test_key_revocation_requires_owner_and_higher_generation(tmp_path):
    store = make_registry(tmp_path)
    store.register("k-1", "owner-a", "TRANSFER_AUTH", 1)
    with pytest.raises(PermissionError, match="key_owner_binding_mismatch"):
        store.revoke("k-1", "owner-b", generation=2)
    with pytest.raises(PermissionError, match="key_generation_not_monotonic"):
        store.revoke("k-1", "owner-a", generation=1)
