"""Bounded deterministic Apollonian personality layer for NORYX7."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json

MAX_NAME = 128
MAX_GRAPH_DEPTH = 32
MAX_GRAPH_NODES = 4096

@dataclass(frozen=True)
class PersonalityProfile:
    name: str
    seed: int
    graph_depth: int = 4
    graph_nodes: int = 64
    exploration_bias: float = 0.5
    verification_bias: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name.encode()) > MAX_NAME:
            raise ValueError("invalid_personality_name")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("invalid_personality_seed")
        if isinstance(self.graph_depth, bool) or not isinstance(self.graph_depth, int) or not 0 <= self.graph_depth <= MAX_GRAPH_DEPTH:
            raise ValueError("invalid_graph_depth")
        if isinstance(self.graph_nodes, bool) or not isinstance(self.graph_nodes, int) or not 1 <= self.graph_nodes <= MAX_GRAPH_NODES:
            raise ValueError("invalid_graph_nodes")
        for value, label in ((self.exploration_bias, "exploration_bias"), (self.verification_bias, "verification_bias")):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"invalid_{label}")

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"NORYX7-PERSONALITY-V1:" + payload).hexdigest()

    def ordering_key(self, item: str) -> str:
        if not isinstance(item, str):
            raise TypeError("personality_item_required")
        return hashlib.sha256(f"{self.seed}:{self.fingerprint}:{item}".encode()).hexdigest()

class PersonalityRegistry:
    """Profiles are immutable once registered for an execution epoch."""
    def __init__(self) -> None:
        self._profiles: dict[str, PersonalityProfile] = {}

    def register(self, agent_id: str, profile: PersonalityProfile) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        if agent_id in self._profiles:
            raise ValueError("personality_already_registered")
        self._profiles[agent_id] = profile

    def get(self, agent_id: str) -> PersonalityProfile:
        if agent_id not in self._profiles:
            raise KeyError("personality_not_registered")
        return self._profiles[agent_id]

    def verify_fingerprint(self, agent_id: str, fingerprint: str) -> bool:
        return self.get(agent_id).fingerprint == fingerprint
