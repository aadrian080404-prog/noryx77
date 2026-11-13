"""Deterministic multi-axis scenario coordinates for bounded adversarial campaigns."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

ENTITY_CLASSES = ("individual", "ai_agent", "organization", "device", "service", "institution", "critical_infrastructure", "supply_chain", "unknown_or_untrusted")
POWER_TIERS = ("p0_minimal", "p1_limited", "p2_moderate", "p3_advanced", "p4_high", "p5_critical", "p6_systemic")
CAPABILITY_CLASSES = ("reconnaissance", "credential_access", "code_execution", "lateral_movement", "persistence", "data_access", "service_disruption", "supply_chain_control")
BEHAVIOR_CLASSES = ("benign", "probing", "evasive", "deceptive", "adaptive", "automated", "collusive", "destructive")
IMPACT_CLASSES = ("none", "confidentiality", "integrity", "availability", "safety", "systemic")
MAX_SCENARIO_CASES = 10_000_000
STRATA_COUNT = len(ENTITY_CLASSES) * len(POWER_TIERS)


@dataclass(frozen=True)
class ScenarioCoordinate:
    case_id: int
    seed: int
    stratum: int
    entity_class: str
    power_tier: str
    capability_class: str
    behavior_class: str
    impact_class: str


def _choice(seed: int, case_id: int, axis: str, values: tuple[str, ...]) -> str:
    material = f"NORYX7_SCENARIO_AXIS_V1:{seed}:{case_id}:{axis}".encode("utf-8")
    index = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % len(values)
    return values[index]


def coordinate_for(seed: int, case_id: int) -> ScenarioCoordinate:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_scenario_seed")
    if isinstance(case_id, bool) or not isinstance(case_id, int) or not 0 <= case_id < MAX_SCENARIO_CASES:
        raise ValueError("scenario_case_out_of_bounds")
    stratum = (case_id + seed) % STRATA_COUNT
    entity_index, power_index = divmod(stratum, len(POWER_TIERS))
    return ScenarioCoordinate(
        case_id=case_id,
        seed=seed,
        stratum=stratum,
        entity_class=ENTITY_CLASSES[entity_index],
        power_tier=POWER_TIERS[power_index],
        capability_class=_choice(seed, case_id, "capability", CAPABILITY_CLASSES),
        behavior_class=_choice(seed, case_id, "behavior", BEHAVIOR_CLASSES),
        impact_class=_choice(seed, case_id, "impact", IMPACT_CLASSES),
    )


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
