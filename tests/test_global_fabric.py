import hashlib

import pytest

from ecosystem.global_fabric import (
    GlobalIdentityAuthorizationFabric,
    GlobalMemoryFabric,
    IdentityAuthorization,
    MemoryLevel,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def test_global_memory_versions_and_redundancy():
    fabric = GlobalMemoryFabric(max_records=2)
    first = fabric.put("r1", MemoryLevel.L2_REGIONAL, b"one", b"provenance", ("a", "b"))
    second = fabric.put("r1", MemoryLevel.L3_DISTRIBUTED, b"two", b"provenance-2", ("b", "c"))
    assert first.version == 1
    assert second.version == 2
    assert fabric.get("r1").payload_digest == digest("two")
    assert fabric.require_redundancy("r1", 2).version == 2


def test_global_memory_rejects_single_replica_when_redundancy_required():
    fabric = GlobalMemoryFabric()
    fabric.put("r1", MemoryLevel.L4_LONG_TERM, b"one", b"p", ("a",))
    with pytest.raises(RuntimeError):
        fabric.require_redundancy("r1", 2)


def test_identity_authorization_is_explicit_and_revocable():
    fabric = GlobalIdentityAuthorizationFabric()
    auth = IdentityAuthorization("id", "session", "device", "operator", ("read",), digest("policy"), digest("grant"))
    fabric.bind(auth)
    assert fabric.authorize("session", "read", digest("policy")) == auth
    with pytest.raises(PermissionError):
        fabric.authorize("session", "write", digest("policy"))
    fabric.revoke("session")
    with pytest.raises(PermissionError):
        fabric.authorize("session", "read", digest("policy"))


def test_existing_session_cannot_be_rebound_to_different_identity():
    fabric = GlobalIdentityAuthorizationFabric()
    first = IdentityAuthorization("id-a", "session", "device-a", "operator", ("read",), digest("policy"), digest("grant-a"))
    second = IdentityAuthorization("id-b", "session", "device-b", "operator", ("read",), digest("policy"), digest("grant-b"))
    fabric.bind(first)
    with pytest.raises(PermissionError, match="binding_mismatch"):
        fabric.bind(second)
    assert fabric.authorize("session", "read", digest("policy")) == first


def test_same_identity_session_may_refresh_authorization_without_swapping_identity():
    fabric = GlobalIdentityAuthorizationFabric()
    first = IdentityAuthorization("id-a", "session", "device-a", "operator", ("read",), digest("policy"), digest("grant-a"))
    refreshed = IdentityAuthorization("id-a", "session", "device-a", "operator", ("read", "write"), digest("policy-2"), digest("grant-b"))
    fabric.bind(first)
    fabric.bind(refreshed)
    with pytest.raises(PermissionError):
        fabric.authorize("session", "read", digest("policy"))
    assert fabric.authorize("session", "write", digest("policy-2")) == refreshed
