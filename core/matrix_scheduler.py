"""Deterministic placement proposals for eligible Matrix nodes."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable
from .matrix_core import NodeProfile, WorkloadRequest, eligible
from .matrix_budget import DeviceConditions, DeviceContributionPolicy


@dataclass(frozen=True)
class PlacementProposal:
    task_id: str
    node_id: str
    failure_domain: str
    dominant_post_placement_utilization: Fraction


def _dominant_utilization(node: NodeProfile, request: WorkloadRequest) -> Fraction:
    capacity, committed = node.envelope.capacity, node.envelope.committed
    dimensions = (
        (committed.cpu_milli + request.resources.cpu_milli, capacity.cpu_milli),
        (committed.memory_bytes + request.resources.memory_bytes, capacity.memory_bytes),
        (committed.storage_bytes + request.resources.storage_bytes, capacity.storage_bytes),
        (committed.bandwidth_bps + request.resources.bandwidth_bps, capacity.bandwidth_bps),
    )
    return max((Fraction(used, total) for used, total in dimensions if total > 0),
               default=Fraction(0, 1))


def propose_placement(nodes: Iterable[NodeProfile], request: WorkloadRequest) -> PlacementProposal | None:
    candidates = [node for node in nodes if eligible(node, request)]
    if not candidates:
        return None
    chosen = min(candidates, key=lambda node: (
        _dominant_utilization(node, request), node.failure_domain, node.node_id))
    return PlacementProposal(request.task_id, chosen.node_id, chosen.failure_domain,
                             _dominant_utilization(chosen, request))


def propose_placement_with_device_policy(
    nodes: Iterable[NodeProfile],
    request: WorkloadRequest,
    policies: dict[str, tuple[DeviceContributionPolicy, DeviceConditions, float]],
) -> PlacementProposal | None:
    """Apply owner device budgets before ranking; estimates must be refreshed locally.

    This is still a proposal. The target supervisor must re-read live sensors and
    atomically reserve resources at dispatch time; coordinator telemetry is advisory.
    """
    candidates = []
    for node in nodes:
        policy_bundle = policies.get(node.node_id)
        if policy_bundle is None or not eligible(node, request):
            continue
        policy, conditions, duration_hours = policy_bundle
        allowed, _reason = policy.permits(conditions, duration_hours)
        if allowed:
            candidates.append(node)
    if not candidates:
        return None
    chosen = min(candidates, key=lambda node: (
        _dominant_utilization(node, request), node.failure_domain, node.node_id))
    return PlacementProposal(request.task_id, chosen.node_id, chosen.failure_domain,
                             _dominant_utilization(chosen, request))
