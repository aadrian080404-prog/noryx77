"""Deterministic adversarial scenario generation and outcome accounting."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .scenario_matrix import MAX_SCENARIO_CASES, coordinate_for


@dataclass(frozen=True)
class AttackScenario:
    scenario_id: str
    seed: int
    difficulty: int
    surface: str
    technique: str
    objective: str
    sequence: tuple[str, ...]
    entity_class: str = "unknown"
    power_tier: str = "p0_minimal"


@dataclass(frozen=True)
class AttackOutcome:
    scenario_id: str
    contained: bool
    recovered: bool
    weakness: str | None


class AdversarialEngine:
    """Generates bounded deterministic scenarios; it never attacks external systems."""

    def __init__(self, *, seed: int = 0, max_scenarios: int = 100_000) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
            raise ValueError("invalid_seed")
        if isinstance(max_scenarios, bool) or not isinstance(max_scenarios, int) or not 1 <= max_scenarios <= MAX_SCENARIO_CASES:
            raise ValueError("invalid_max_scenarios")
        self.seed = seed
        self.max_scenarios = max_scenarios

    def scenario(self, index: int, *, difficulty: int = 1) -> AttackScenario:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < self.max_scenarios:
            raise IndexError("scenario_index_out_of_range")
        if isinstance(difficulty, bool) or not isinstance(difficulty, int) or not 1 <= difficulty <= 100:
            raise ValueError("invalid_difficulty")
        digest = hashlib.sha256(f"{self.seed}:{index}:{difficulty}".encode()).hexdigest()
        surfaces = ("identity", "network", "memory", "tool", "runtime", "supply_chain", "sandbox")
        techniques = ("replay", "tamper", "substitution", "escalation", "escape", "exfiltration", "corruption")
        objectives = ("access", "persist", "execute", "exfiltrate", "disrupt")
        surface = surfaces[int(digest[:8], 16) % len(surfaces)]
        technique = techniques[int(digest[8:16], 16) % len(techniques)]
        objective = objectives[int(digest[16:24], 16) % len(objectives)]
        seq_len = 1 + min(8, difficulty // 15)
        sequence = tuple(techniques[int(digest[(24 + i * 2):(26 + i * 2)], 16) % len(techniques)] for i in range(seq_len))
        coordinate = coordinate_for(self.seed, index)
        return AttackScenario(
            f"adv-{digest[:24]}", self.seed, difficulty, surface, technique,
            objective, sequence, coordinate.entity_class, coordinate.power_tier,
        )
