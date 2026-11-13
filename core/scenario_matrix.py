"""Balanced deterministic adversarial matrix across entity, power, capability, behavior and impact."""
from __future__ import annotations

from dataclasses import dataclass

ENTITY_CLASSES = (
    "individual", "ai_agent", "organization", "device", "service",
    "institution", "critical_infrastructure", "supply_chain", "unknown_or_untrusted",
)
POWER_TIERS = (
    "p0_minimal", "p1_limited", "p2_moderate", "p3_advanced",
    "p4_high", "p5_critical", "p6_systemic",
)
CAPABILITY_CLASSES = (
    "credential_access", "code_execution", "network_control", "data_access",
    "persistence", "physical_access", "model_manipulation", "supply_chain_control",
)
BEHAVIOR_CLASSES = (
    "opportunistic", "stealthy", "persistent", "adaptive",
    "collusive", "deceptive", "destructive", "exfiltrative",
)
IMPACT_CLASSES = (
    "confidentiality", "integrity", "availability",
    "safety", "financial", "systemic",
)
MAX_SCENARIO_CASES = 10_000_000
STRATA_COUNT = (
    len(ENTITY_CLASSES) * len(POWER_TIERS) * len(CAPABILITY_CLASSES)
    * len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES)
)


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


def coordinate_for(seed: int, case_id: int) -> ScenarioCoordinate:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_scenario_seed")
    if isinstance(case_id, bool) or not isinstance(case_id, int) or not 0 <= case_id < MAX_SCENARIO_CASES:
        raise ValueError("scenario_case_out_of_bounds")
    stratum = (case_id + seed) % STRATA_COUNT
    remainder = stratum
    entity_index, remainder = divmod(
        remainder,
        len(POWER_TIERS) * len(CAPABILITY_CLASSES) * len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES),
    )
    power_index, remainder = divmod(
        remainder,
        len(CAPABILITY_CLASSES) * len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES),
    )
    capability_index, remainder = divmod(
        remainder, len(BEHAVIOR_CLASSES) * len(IMPACT_CLASSES)
    )
    behavior_index, impact_index = divmod(remainder, len(IMPACT_CLASSES))
    return ScenarioCoordinate(
        case_id,
        seed,
        stratum,
        ENTITY_CLASSES[entity_index],
        POWER_TIERS[power_index],
        CAPABILITY_CLASSES[capability_index],
        BEHAVIOR_CLASSES[behavior_index],
        IMPACT_CLASSES[impact_index],
    )


def expected_stratum_counts(cases: int, *, seed: int = 0) -> dict[tuple[str, str, str, str, str], int]:
    if isinstance(cases, bool) or not isinstance(cases, int) or not 1 <= cases <= MAX_SCENARIO_CASES:
        raise ValueError("invalid_scenario_case_count")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
        raise ValueError("invalid_scenario_seed")
    base, remainder = divmod(cases, STRATA_COUNT)
    counts = {
        (entity, power, capability, behavior, impact): base
        for entity in ENTITY_CLASSES
        for power in POWER_TIERS
        for capability in CAPABILITY_CLASSES
        for behavior in BEHAVIOR_CLASSES
        for impact in IMPACT_CLASSES
    }
    for offset in range(remainder):
        coordinate = coordinate_for(seed, offset)
        key = (
            coordinate.entity_class,
            coordinate.power_tier,
            coordinate.capability_class,
            coordinate.behavior_class,
            coordinate.impact_class,
        )
        counts[key] += 1
    return counts
