import pytest
from .matrix_core import ContributionGrant, ResourceVector
from .matrix_grants import DurableGrantRegistry


def grant(generation, enabled=True):
    return ContributionGrant("grant-1", enabled, generation,
        ResourceVector(1000, 2_000_000, 3_000_000, 4_000_000),
        frozenset({"compute", "verification"}), False)


def test_durable_grant_survives_restart_and_revocation_is_fail_closed(tmp_path):
    path = tmp_path / "grants.db"
    registry = DurableGrantRegistry(path)
    saved = registry.put("node-1", "owner-1", grant(1))
    assert saved.grant.enabled and saved.grant.generation == 1
    reopened = DurableGrantRegistry(path)
    assert reopened.get("grant-1") == saved
    revoked = reopened.revoke("grant-1", expected_generation=1)
    assert not revoked.grant.enabled
    assert revoked.grant.generation == 2
    assert revoked.grant.max_resources == ResourceVector()
    assert revoked.grant.allowed_workloads == frozenset()
    assert DurableGrantRegistry(path).get("grant-1") == revoked


def test_durable_grant_compare_and_swap_blocks_stale_updates(tmp_path):
    path = tmp_path / "grants.db"
    registry = DurableGrantRegistry(path)
    registry.put("node-1", "owner-1", grant(1))
    with pytest.raises(PermissionError, match="grant_generation_must_increase"):
        registry.put("node-1", "owner-1", grant(1))
    with pytest.raises(PermissionError, match="grant_generation_compare_and_swap_failed"):
        registry.revoke("grant-1", expected_generation=0)


def test_durable_grant_cannot_be_silently_rebound_to_another_owner(tmp_path):
    registry = DurableGrantRegistry(tmp_path / "grants.db")
    registry.put("node-1", "owner-1", grant(1))
    with pytest.raises(PermissionError, match="grant_owner_or_node_binding_immutable"):
        registry.put("node-2", "owner-2", grant(2))
