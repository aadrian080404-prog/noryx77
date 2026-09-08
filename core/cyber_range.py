"""Isolated cyber-range contract for NORYX7 red-team simulation.

This module models offensive security workflows without providing mechanisms for
compromising real systems. Targets are synthetic assets, actions are symbolic,
and every operation requires an explicit owner authorization token.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Mapping

MAX_TARGETS = 256
MAX_ACTIONS = 512
MAX_ID = 256


class AttackPhase(str, Enum):
    RECON = "recon"
    ENUMERATION = "enumeration"
    EXPLOIT_SIMULATION = "exploit_simulation"
    PRIVILEGE_SIMULATION = "privilege_simulation"
    LATERAL_SIMULATION = "lateral_simulation"
    IMPACT_SIMULATION = "impact_simulation"
    VERIFICATION = "verification"
    REPORT = "report"


@dataclass(frozen=True)
class SyntheticTarget:
    target_id: str
    vulnerabilities: tuple[str, ...] = ()
    trust_zone: str = "sandbox"

    def __post_init__(self) -> None:
        if not isinstance(self.target_id, str) or not self.target_id.strip() or len(self.target_id) > MAX_ID:
            raise ValueError("invalid_synthetic_target")
        if self.trust_zone != "sandbox":
            raise ValueError("cyber_range_requires_sandbox_target")
        if len(self.vulnerabilities) > 64 or any(not isinstance(v, str) or not v.strip() for v in self.vulnerabilities):
            raise ValueError("invalid_vulnerability_catalog")


@dataclass(frozen=True)
class OwnerAuthorization:
    principal_id: str
    authorization_id: str
    expires_at: int

    def valid_for(self, principal_id: str, now: int) -> bool:
        return (
            isinstance(principal_id, str) and principal_id == self.principal_id
            and isinstance(now, int) and now <= self.expires_at
            and bool(self.authorization_id.strip())
        )


@dataclass(frozen=True)
class SimulatedAction:
    phase: AttackPhase
    technique: str
    target_id: str
    evidence: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationReport:
    target_id: str
    actions: tuple[SimulatedAction, ...]
    verified: bool


class CyberRange:
    """Bounded simulation environment; never dispatches arbitrary network code."""

    def __init__(self, *, max_actions: int = MAX_ACTIONS) -> None:
        if isinstance(max_actions, bool) or not 1 <= max_actions <= MAX_ACTIONS:
            raise ValueError("invalid_max_actions")
        self._max_actions = max_actions
        self._targets: dict[str, SyntheticTarget] = {}
        self._lock = RLock()

    def register_target(self, target: SyntheticTarget) -> None:
        if not isinstance(target, SyntheticTarget):
            raise TypeError("synthetic_target_required")
        with self._lock:
            if len(self._targets) >= MAX_TARGETS and target.target_id not in self._targets:
                raise RuntimeError("target_capacity_exceeded")
            self._targets[target.target_id] = target

    def simulate(self, *, target_id: str, principal_id: str, authorization: OwnerAuthorization,
                 now: int, techniques: tuple[str, ...]) -> SimulationReport:
        if not isinstance(authorization, OwnerAuthorization) or not authorization.valid_for(principal_id, now):
            raise PermissionError("owner_authorization_required")
        if not techniques or len(techniques) > self._max_actions:
            raise ValueError("invalid_simulation_plan")
        if any(not isinstance(t, str) or not t.strip() for t in techniques):
            raise ValueError("invalid_simulation_technique")
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                raise KeyError("synthetic_target_not_found")
            phases = (
                AttackPhase.RECON, AttackPhase.ENUMERATION,
                AttackPhase.EXPLOIT_SIMULATION, AttackPhase.PRIVILEGE_SIMULATION,
                AttackPhase.LATERAL_SIMULATION, AttackPhase.IMPACT_SIMULATION,
                AttackPhase.VERIFICATION, AttackPhase.REPORT,
            )
            actions = tuple(
                SimulatedAction(phases[index % len(phases)], technique, target.target_id,
                                {"simulation": "true", "target_zone": target.trust_zone})
                for index, technique in enumerate(techniques)
            )
            return SimulationReport(target.target_id, actions, verified=True)
