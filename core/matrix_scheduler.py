"""Deterministic placement proposals for eligible Matrix nodes.

A proposal is not a reservation. The target node must atomically reserve locally
and return confirmation before a coordinator treats placement as committed.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .matrix_core import NodeProfile, WorkloadRequest, eligible


@dataclass(frozen=True)
class PlacementProposal:
    task_id: str
    node_id: str
    failure_domain: str
    dominant_post_placement_utilization: Fraction


def _dominant_utilization(node: NodeProfile, request: WorkloadRequest) -> Fraction:
    capacity = node.envelope.capacity
    committed = node.envelope.committed
    dimensions = (
        (committed.cpu_milli + request.resources.cpu_milli, capacity.cpu_milli),
        (committed.memory_bytes + request.resources.memory_bytes, capacity.memory_bytes),
        (committed.storage_bytes + request.resources.storage_bytes, capacity.storage_bytes),
        (committed.bandwidth_bps + request.resources.bandwidth_bps, capacity.bandwidth_bps),
    )
    ratios = [Fraction(used, total) for used, total in dimensions if total > 0]
    return max(ratios, default=Fraction(0, 1))


def propose_placement(
    nodes: Iterable[NodeProfile], request: WorkloadRequest
) -> PlacementProposal | None:
    candidates = [
        node for node in nodes
        if eligible(node, request)
    ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda node: (
            _dominant_utilization(node, request),
            node.failure_domain,
            node.node_id,
        ),
    )
    chosen = ranked[0]
    return PlacementProposal(
        request.task_id, chosen.node_id, chosen.failure_domain,
        _dominant_utilization(chosen, request),
    )
