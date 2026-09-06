"""Unified control-plane composition for the NORYX7 architecture.

This module wires policy, verification, defense, recovery, observability and
supply-chain boundaries without granting cognition components security authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .adversarial import AdversarialEngine
from .defense import DefenseController, DefenseMode
from .observability import EventKind, SecurityEventBus
from .personality import ApollonianPersonality
from .recovery import RecoveryController, RecoveryState
from .supply_chain import ArtifactManifest, SupplyChainVerifier


@dataclass(frozen=True)
class ControlPlaneStatus:
    defense_mode: DefenseMode
    recovery_state: RecoveryState
    event_count: int


class Noryx7ControlPlane:
    """Security/control-plane composition root with fail-closed recovery flow."""

    def __init__(self, *, supply_chain: SupplyChainVerifier, personality: ApollonianPersonality | None = None) -> None:
        if not isinstance(supply_chain, SupplyChainVerifier):
            raise TypeError("supply_chain_must_be_verifier")
        if personality is not None and not isinstance(personality, ApollonianPersonality):
            raise TypeError("personality_must_be_ApollonianPersonality")
        self.supply_chain = supply_chain
        self.personality = personality
        self.events = SecurityEventBus()
        self.recovery = RecoveryController()
        self.adversarial = AdversarialEngine()
        self.defense = DefenseController()
        # The control-plane core is the only component pre-trusted for recovery.
        self.defense.trust_component("core")

    def _observe(self, kind: EventKind, reason: str, *, severity: int = 80) -> None:
        """Record a deterministic evidence digest before exposing a transition."""
        evidence = hashlib.sha256(
            f"noryx7/control-plane/v1|{kind.value}|{reason}|{self.recovery.epoch}".encode("utf-8")
        ).hexdigest()
        self.events.publish(
            kind,
            component="control-plane",
            severity=severity,
            evidence_digest=evidence,
        )

    def admit_artifact(self, manifest: ArtifactManifest) -> bool:
        return self.supply_chain.verify(manifest)

    def incident(self) -> None:
        if self.recovery.state is RecoveryState.NORMAL:
            self.recovery.incident()
        if self.recovery.state is RecoveryState.INCIDENT:
            self.recovery.lockdown()
            self.defense.enter_lockdown("control-plane incident")
            self.recovery.trusted_only()
            self._observe(EventKind.INTEGRITY_VIOLATION, "control-plane incident", severity=100)

    def begin_recovery(self) -> None:
        if self.recovery.state is not RecoveryState.TRUSTED_ONLY:
            raise PermissionError("trusted_only_state_required")
        self.recovery.recover()
        self.defense.enter_recovery()
        self._observe(EventKind.PROCESS_ANOMALY, "recovery started")

    def mark_verified(self) -> None:
        if self.recovery.state is not RecoveryState.RECOVERY:
            raise PermissionError("recovery_state_required")
        self.defense.finish_recovery(verified_components=("core",))
        self.recovery.verify(True)
        self._observe(EventKind.INTEGRITY_VIOLATION, "recovery verified", severity=60)

    def resume_normal(self) -> None:
        if self.recovery.state is not RecoveryState.VERIFIED:
            raise PermissionError("verified_state_required")
        self.defense.resume_normal()
        self.recovery.resume()
        self._observe(EventKind.POLICY_VIOLATION, "normal operation resumed", severity=40)

    def status(self) -> ControlPlaneStatus:
        return ControlPlaneStatus(self.defense.mode, self.recovery.state, len(self.events.snapshot()))
