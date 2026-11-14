"""Balanced deterministic scenario strata by entity class and capability/power tier."""
from __future__ import annotations
from dataclasses import dataclass

ENTITY_CLASSES = ("individual", "ai_agent", "organization", "device", "service", "institution", "critical_infrastructure", "supply_chain", "unknown_or_untrusted")
POWER_TIERS = ("p0_minimal", "p1_limited", "p2_moderate", "p3_advanced", "p4_high", "p5_critical", "p6_systemic")
MAX_SCENARIO_CASES = 10_000_000
STRATA_COUNT = len(ENTITY_CLASSES) * len(POWER_TIERS)

@dataclass(frozen=True)
class ScenarioCoordinate:
    case_id: int
    seed: int
    stratum: int
    entity_class: str
    power_tier: str

def coordinate_for(seed: int, case_id: int) -> ScenarioCoordinate:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_scenario_seed")
    if isinstance(case_id, bool) or not isinstance(case_id, int) or not 0 <= case_id < MAX_SCENARIO_CASES:
        raise ValueError("scenario_case_out_of_bounds")
    stratum = (case_id + seed) % STRATA_COUNT
    entity_index, power_index = divmod(stratum, len(POWER_TIERS))
    return ScenarioCoordinate(case_id, seed, stratum, ENTITY_CLASSES[entity_index], POWER_TIERS[power_index])

def expected_stratum_counts(cases: int, *, seed: int = 0) -> dict[tuple[str, str], int]:
    if isinstance(cases, bool) or not isinstance(cases, int) or not 1 <= cases <= MAX_SCENARIO_CASES:
        raise ValueError("invalid_scenario_case_count")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_scenario_seed")
    base, remainder = divmod(cases, STRATA_COUNT)
    counts = {(entity, power): base for entity in ENTITY_CLASSES for power in POWER_TIERS}
    for offset in range(remainder):
        entity_index, power_index = divmod((offset + seed) % STRATA_COUNT, len(POWER_TIERS))
        counts[(ENTITY_CLASSES[entity_index], POWER_TIERS[power_index])] += 1
    return counts
