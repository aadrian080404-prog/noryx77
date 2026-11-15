from fractions import Fraction
from .matrix_core import (ContributionGrant, NodeProfile, ResourceEnvelope,
                          ResourceVector, WorkloadRequest)
from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_scheduler import propose_placement_with_device_policy


def test_scheduler_filters_nodes_using_owner_device_policy():
    grant = ContributionGrant("grant", True, 1, ResourceVector(2000, 2_000_000),
                              frozenset({"compute"}))
    def node(node_id, failure_domain):
        return NodeProfile(node_id, failure_domain, True, True,
            ResourceEnvelope(ResourceVector(4000, 4_000_000), ResourceVector(), ResourceVector(500, 500_000)),
            grant)
    request = WorkloadRequest("task", "compute", ResourceVector(500, 500_000), 1)
    policy = DeviceContributionPolicy(True, 30, 42, 4, 1_000_000, 8, ((0, 1000),))
    cool = DeviceConditions(80, 35, 2, 500_000, 100)
    hot = DeviceConditions(80, 49, 2, 500_000, 100)
    result = propose_placement_with_device_policy(
        [node("a", "region-a"), node("b", "region-b")], request,
        {"a": (policy, hot, 1), "b": (policy, cool, 1)}
    )
    assert result is not None
    assert result.node_id == "b"
    assert result.dominant_post_placement_utilization == Fraction(1, 8)
