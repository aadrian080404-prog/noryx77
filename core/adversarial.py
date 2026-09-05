"""Deterministic adversarial scenario generation and outcome accounting."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

MAX_SCENARIOS = 1_000_000


@dataclass(frozen=True)
class AttackScenario:
    scenario_id: str
    seed: int
    difficulty: int
    surface: str
    technique: str
    objective: str
    sequence: tuple[str, ...]


@dataclass(frozen=True)
class AttackOutcome:
    scenario_id: str
    contained: bool
    recovered: bool
    weakness: str | None


class AdversarialEngine:
    """Generates bounded deterministic scenarios; it never attacks external systems."""

    def __init__(self, *, seed: int = 0, max_scenarios: int = 100_000) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("invalid_seed")
        if not 1 <= max_scenarios <= MAX_SCENARIOS:
            raise ValueError("invalid_max_scenarios")
        self.seed = seed
        self.max_scenarios = max_scenarios

    def scenario(self, index: int, *, difficulty: int = 1) -> AttackScenario:
        if not 0 <= index < self.max_scenarios:
            raise IndexError("scenario_index_out_of_range")
        if not 1 <= difficulty <= 100:
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
        return AttackScenario(f"adv-{digest[:24]}", self.seed, difficulty, surface, technique, objective, sequence)
