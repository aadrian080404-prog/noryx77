"""Bounded distributed topology and compartment placement primitives."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
class Zone(str, Enum):
    CLIENT="client"; EDGE="edge"; CLOUD="cloud"; HARDWARE="hardware"; OFFLINE="offline"
@dataclass(frozen=True)
class ComponentPlacement:
    component_id: str
    zone: Zone
    shard: int
    def __post_init__(self) -> None:
        if not isinstance(self.component_id,str) or not self.component_id.strip(): raise ValueError("invalid_component_id")
        if isinstance(self.shard,bool) or not isinstance(self.shard,int) or not 0 <= self.shard < 4096: raise ValueError("invalid_shard")
class Topology:
    def __init__(self) -> None: self._placements: dict[str,ComponentPlacement] = {}
    def place(self, placement: ComponentPlacement) -> None:
        if placement.component_id in self._placements: raise ValueError("component_already_placed")
        self._placements[placement.component_id]=placement
    def get(self, component_id: str) -> ComponentPlacement:
        return self._placements[component_id]
    def snapshot(self) -> tuple[ComponentPlacement,...]: return tuple(self._placements.values())
