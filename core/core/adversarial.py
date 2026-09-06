"""Deterministic adversarial scenario generator for large-scale evaluation."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
MAX_SCENARIOS = 1_000_000
@dataclass(frozen=True)
class AttackScenario:
    scenario_id: str
    surface: str
    technique: str
    objective: str
    difficulty: int
    sequence: int
class AdversarialScenarioEngine:
    surfaces = ("identity", "network", "process", "memory", "tool", "model", "device", "supply_chain", "recovery")
    techniques = ("spoof", "replay", "tamper", "escalate", "escape", "lateral", "exfiltrate", "resource_exhaustion", "policy_confusion")
    objectives = ("deny", "isolate", "persist", "exfiltrate", "alter_state", "bypass_policy")
    def __init__(self, seed: int = 0) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("invalid_adversarial_seed")
        self.seed = seed
    def scenario(self, index: int) -> AttackScenario:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < MAX_SCENARIOS:
            raise ValueError("scenario_index_out_of_bounds")
        digest = hashlib.sha256(f"NORYX7-ATTACK-V1:{self.seed}:{index}".encode()).digest()
        surface = self.surfaces[digest[0] % len(self.surfaces)]
        technique = self.techniques[digest[1] % len(self.techniques)]
        objective = self.objectives[digest[2] % len(self.objectives)]
        difficulty = 1 + digest[3] % 100
        return AttackScenario(f"atk-{self.seed}-{index}", surface, technique, objective, difficulty, index)
    def batch(self, start: int, count: int) -> tuple[AttackScenario, ...]:
        if count < 0 or start < 0 or start + count > MAX_SCENARIOS:
            raise ValueError("attack_batch_out_of_bounds")
        return tuple(self.scenario(i) for i in range(start, start + count))
