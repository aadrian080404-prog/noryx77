"""Deterministic, bounded Apollonian/Pythagorean agent personality metadata.

Personality is a cognition modifier only. It never participates in authentication,
authorization, cryptographic verification, recovery, or security policy decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

MAX_SEED_BYTES = 256
MAX_GRAPH_DEPTH = 16
MAX_NODES = 4096


@dataclass(frozen=True)
class PersonalityProfile:
    agent_id: str
    seed: int
    graph_depth: int = 4
    node_budget: int = 64
    exploration_bias: float = 0.5
    verification_bias: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.agent_id, str) or not self.agent_id:
            raise ValueError("invalid_agent_id")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("invalid_seed")
        if not 0 <= self.graph_depth <= MAX_GRAPH_DEPTH:
            raise ValueError("invalid_graph_depth")
        if not 1 <= self.node_budget <= MAX_NODES:
            raise ValueError("invalid_node_budget")
        for value in (self.exploration_bias, self.verification_bias):
            if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                raise ValueError("invalid_bias")

    @property
    def fingerprint(self) -> str:
        raw = f"{self.agent_id}|{self.seed}|{self.graph_depth}|{self.node_budget}|{self.exploration_bias:.12f}|{self.verification_bias:.12f}".encode()
        return hashlib.sha256(raw).hexdigest()


class ApollonianPersonality:
    """Produces deterministic bounded ordering signals for cognitive exploration."""

    def __init__(self, profile: PersonalityProfile) -> None:
        if not isinstance(profile, PersonalityProfile):
            raise TypeError("profile_must_be_PersonalityProfile")
        self._profile = profile

    @property
    def profile(self) -> PersonalityProfile:
        return self._profile

    def rank(self, candidates: tuple[str, ...]) -> tuple[str, ...]:
        if len(candidates) > self._profile.node_budget:
            raise ValueError("candidate_budget_exceeded")
        scored = []
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, str):
                raise TypeError("candidate_must_be_string")
            digest = hashlib.sha256(f"{self._profile.seed}:{index}:{candidate}".encode()).digest()
            score = int.from_bytes(digest[:8], "big") / 2**64
            scored.append((score, candidate))
        return tuple(item[1] for item in sorted(scored))
