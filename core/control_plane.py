"""Unified control-plane composition for the NORYX7 architecture.

This module wires policy, verification, defense, recovery, observability and
supply-chain boundaries without granting cognition components security authority.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adversarial import AdversarialEngine
from .defense import DefenseController, DefenseMode
from .observability import SecurityEventBus
from .personality import ApollonianPersonality
from .recovery_plane import RecoveryController, RecoveryState
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

    def admit_artifact(self, manifest: ArtifactManifest) -> bool:
        return self.supply_chain.verify(manifest)

    def incident(self) -> None:
        if self.recovery.state is RecoveryState.NORMAL:
            self.recovery.transition(RecoveryState.INCIDENT)
        if self.recovery.state is RecoveryState.INCIDENT:
            self.recovery.transition(RecoveryState.LOCKDOWN)
            self.defense.enter_lockdown("control-plane incident")
            self.recovery.transition(RecoveryState.TRUSTED_ONLY)

    def begin_recovery(self) -> None:
        if self.recovery.state is not RecoveryState.TRUSTED_ONLY:
            raise PermissionError("trusted_only_state_required")
        self.recovery.transition(RecoveryState.RECOVERY)

    def mark_verified(self) -> None:
        if self.recovery.state is not RecoveryState.RECOVERY:
            raise PermissionError("recovery_state_required")
        self.recovery.transition(RecoveryState.VERIFIED)

    def status(self) -> ControlPlaneStatus:
        return ControlPlaneStatus(self.defense.mode, self.recovery.state, len(self.events.snapshot()))
