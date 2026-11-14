import pytest

from .matrix_core import (
    ContributionGrant,
    LocalReservationBook,
    NodeProfile,
    ResourceEnvelope,
    ResourceVector,
    WorkloadRequest,
    eligible,
)


def make_node(*, enabled=True, generation=3, attested=True, sandbox=True, data=False):
    capacity = ResourceVector(cpu_milli=4000, memory_bytes=8_000_000, storage_bytes=1_000_000, bandwidth_bps=10_000)
    reserve = ResourceVector(cpu_milli=1000, memory_bytes=2_000_000)
    grant = ContributionGrant(
        "owner-grant", enabled=enabled, generation=generation,
        max_resources=ResourceVector(cpu_milli=2000, memory_bytes=4_000_000),
        allowed_workloads=frozenset({"verification", "compression"}),
        allow_user_data=data,
    )
    return NodeProfile(
        "node-a", "home-lan-a", attested, sandbox,
        ResourceEnvelope(capacity, ResourceVector(), reserve), grant,
    )


def make_request(**overrides):
    values = dict(
        task_id="task-1", workload_class="verification",
        resources=ResourceVector(cpu_milli=500, memory_bytes=500_000),
        generation=3,
    )
    values.update(overrides)
    return WorkloadRequest(**values)


def test_contribution_is_off_by_default():
    node = make_node(enabled=False)
    assert not eligible(node, make_request())


def test_node_requires_explicit_workload_and_generation_grant():
    node = make_node()
    assert eligible(node, make_request())
    assert not eligible(node, make_request(workload_class="model-training"))
    assert not eligible(node, make_request(generation=2))


def test_unattested_or_unsandboxed_node_is_rejected():
    assert not eligible(make_node(attested=False), make_request())
    assert not eligible(make_node(sandbox=False), make_request())


def test_user_data_access_is_denied_by_default():
    assert not eligible(make_node(data=False), make_request(requires_user_data=True))
    assert eligible(make_node(data=True), make_request(requires_user_data=True))


def test_resource_reserve_is_never_allocated_to_work():
    node = make_node()
    request = make_request(resources=ResourceVector(cpu_milli=3000))
    assert not eligible(node, request)
    book = LocalReservationBook(node)
    with pytest.raises(PermissionError):
        book.reserve(request)


def test_reservations_are_bounded_and_released():
    book = LocalReservationBook(make_node())
    book.reserve(make_request())
    assert book.node.envelope.committed.cpu_milli == 500
    with pytest.raises(ValueError, match="task_already_reserved"):
        book.reserve(make_request())
    book.release("task-1")
    assert book.node.envelope.committed.cpu_milli == 0
    with pytest.raises(KeyError):
        book.release("task-1")


def test_revoke_invalidates_generation_and_reports_running_tasks():
    book = LocalReservationBook(make_node())
    book.reserve(make_request())
    revoked = ContributionGrant(
        "owner-grant", enabled=False, generation=4,
        max_resources=ResourceVector(), allowed_workloads=frozenset(),
    )
    assert book.revoke(revoked) == ("task-1",)
    assert not eligible(book.node, make_request(generation=4))
    assert book.node.envelope.committed.cpu_milli == 0


def test_revocation_requires_monotonic_generation_and_same_grant():
    book = LocalReservationBook(make_node())
    with pytest.raises(ValueError):
        book.revoke(ContributionGrant("other", enabled=False, generation=4))
    with pytest.raises(ValueError):
        book.revoke(ContributionGrant("owner-grant", enabled=False, generation=3))


def test_invalid_resource_values_and_reserve_are_rejected():
    with pytest.raises(ValueError):
        ResourceVector(cpu_milli=-1)
    with pytest.raises(ValueError):
        ResourceEnvelope(
            ResourceVector(cpu_milli=1000), ResourceVector(), ResourceVector(cpu_milli=1001)
        )


def test_request_cannot_claim_more_than_owner_grant():
    node = make_node()
    assert not eligible(node, make_request(resources=ResourceVector(cpu_milli=2500)))



def test_owner_quota_applies_to_aggregate_concurrent_workloads():
    book = LocalReservationBook(make_node())
    book.reserve(make_request(task_id="task-a", resources=ResourceVector(cpu_milli=1500)))
    with pytest.raises(PermissionError, match="owner_contribution_quota_exceeded"):
        book.reserve(make_request(task_id="task-b", resources=ResourceVector(cpu_milli=1000)))
    assert book.node.envelope.committed.cpu_milli == 1500
