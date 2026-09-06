"""Distributed NORYX7 topology and compartment contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeRole(str, Enum):
    CLIENT = "client"
    EDGE = "edge"
    CLOUD = "cloud"
    HARDWARE = "hardware"
    OFFLINE = "offline"


@dataclass(frozen=True)
class NodeDescriptor:
    node_id: str
    role: NodeRole
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ShardDescriptor:
    shard_id: str
    node_id: str
    encrypted: bool = True


class DistributedTopology:
    """Tracks placement without allowing one node to claim the complete system."""

    def __init__(self, nodes: tuple[NodeDescriptor, ...] = ()) -> None:
        self._nodes = {node.node_id: node for node in nodes}
        self._shards: dict[str, ShardDescriptor] = {}

    def add_node(self, node: NodeDescriptor) -> None:
        if not isinstance(node, NodeDescriptor) or not node.node_id:
            raise ValueError("invalid_node")
        if node.node_id in self._nodes:
            raise ValueError("node_already_registered")
        self._nodes[node.node_id] = node

    def place_shard(self, shard: ShardDescriptor) -> None:
        if not isinstance(shard, ShardDescriptor) or not shard.encrypted:
            raise ValueError("invalid_shard")
        if shard.node_id not in self._nodes:
            raise ValueError("unknown_node")
        if shard.shard_id in self._shards:
            raise ValueError("shard_already_registered")
        self._shards[shard.shard_id] = shard

    def node(self, node_id: str) -> NodeDescriptor | None:
        return self._nodes.get(node_id)

    def shards_for(self, node_id: str) -> tuple[ShardDescriptor, ...]:
        return tuple(shard for shard in self._shards.values() if shard.node_id == node_id)
