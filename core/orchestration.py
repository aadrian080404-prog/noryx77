"""Bounded orchestration boundary for the NORYX7 interaction plane.

This module coordinates *references* between fronts without granting execution
authority. Raw user content never enters the orchestration envelope; execution
remains behind the existing policy, capability, authorization and verification
boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Mapping

from .interaction_context import InteractionContext

MAX_OPERATION = 256
MAX_REFERENCE = 256
MAX_METADATA = 32


class OrchestrationStage(str, Enum):
    RECEIVED = "received"
    UNDERSTOOD = "understood"
    REPRESENTED = "represented"
    ROUTED = "routed"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMMITTED = "committed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class OrchestrationEnvelope:
    request_id: str
    principal_id: str
    operation: str
    interaction_context: InteractionContext
    stage: OrchestrationStage = OrchestrationStage.RECEIVED
    intent_digest: str = ""
    plan_digest: str = ""
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.request_id, "request_id"),
            (self.principal_id, "principal_id"),
            (self.operation, "operation"),
        ):
            if not isinstance(value, str) or not value.strip() or len(value.encode()) > MAX_REFERENCE:
                raise ValueError(f"invalid_{name}")
        if not isinstance(self.interaction_context, InteractionContext):
            raise TypeError("interaction_context_required")
        if not isinstance(self.stage, OrchestrationStage):
            raise TypeError("invalid_stage")
        for value, name in ((self.intent_digest, "intent_digest"), (self.plan_digest, "plan_digest")):
            if not isinstance(value, str) or len(value) > 64:
                raise ValueError(f"invalid_{name}")
        if not isinstance(self.metadata, tuple) or len(self.metadata) > MAX_METADATA:
            raise ValueError("metadata_capacity_exceeded")
        for item in self.metadata:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("invalid_metadata")
            if any(not isinstance(v, str) or len(v.encode()) > MAX_REFERENCE for v in item):
                raise ValueError("invalid_metadata")


@dataclass(frozen=True)
class OrchestrationTransition:
    previous: OrchestrationStage
    current: OrchestrationStage
    envelope_digest: str


_ALLOWED_TRANSITIONS: Mapping[OrchestrationStage, frozenset[OrchestrationStage]] = {
    OrchestrationStage.RECEIVED: frozenset({OrchestrationStage.UNDERSTOOD, OrchestrationStage.REJECTED}),
    OrchestrationStage.UNDERSTOOD: frozenset({OrchestrationStage.REPRESENTED, OrchestrationStage.REJECTED}),
    OrchestrationStage.REPRESENTED: frozenset({OrchestrationStage.ROUTED, OrchestrationStage.REJECTED}),
    OrchestrationStage.ROUTED: frozenset({OrchestrationStage.PLANNED, OrchestrationStage.REJECTED}),
    OrchestrationStage.PLANNED: frozenset({OrchestrationStage.EXECUTING, OrchestrationStage.REJECTED}),
    OrchestrationStage.EXECUTING: frozenset({OrchestrationStage.VERIFYING, OrchestrationStage.REJECTED}),
    OrchestrationStage.VERIFYING: frozenset({OrchestrationStage.COMMITTED, OrchestrationStage.REJECTED}),
    OrchestrationStage.COMMITTED: frozenset(),
    OrchestrationStage.REJECTED: frozenset(),
}


class OrchestrationCoordinator:
    """State-machine boundary; it cannot execute tools or grant capabilities."""

    @staticmethod
    def transition(envelope: OrchestrationEnvelope, target: OrchestrationStage) -> tuple[OrchestrationEnvelope, OrchestrationTransition]:
        if not isinstance(envelope, OrchestrationEnvelope):
            raise TypeError("orchestration_envelope_required")
        if not isinstance(target, OrchestrationStage):
            raise TypeError("invalid_target_stage")
        if target not in _ALLOWED_TRANSITIONS[envelope.stage]:
            raise ValueError("invalid_orchestration_transition")
        updated = OrchestrationEnvelope(
            request_id=envelope.request_id,
            principal_id=envelope.principal_id,
            operation=envelope.operation,
            interaction_context=envelope.interaction_context,
            stage=target,
            intent_digest=envelope.intent_digest,
            plan_digest=envelope.plan_digest,
            metadata=envelope.metadata,
        )
        return updated, OrchestrationTransition(envelope.stage, target, OrchestrationCoordinator.digest(updated))

    @staticmethod
    def reject(envelope: OrchestrationEnvelope) -> tuple[OrchestrationEnvelope, OrchestrationTransition]:
        """Fail closed from any non-terminal stage without permitting recovery by transition."""
        if not isinstance(envelope, OrchestrationEnvelope):
            raise TypeError("orchestration_envelope_required")
        if envelope.stage in (OrchestrationStage.COMMITTED, OrchestrationStage.REJECTED):
            raise ValueError("terminal_orchestration_stage")
        return OrchestrationCoordinator.transition(envelope, OrchestrationStage.REJECTED)

    @staticmethod
    def with_intent_digest(envelope: OrchestrationEnvelope, intent_material: str) -> OrchestrationEnvelope:
        if not isinstance(intent_material, str) or not intent_material.strip():
            raise ValueError("intent_material_required")
        if len(intent_material.encode()) > MAX_REFERENCE * 4:
            raise ValueError("intent_material_too_large")
        return OrchestrationEnvelope(
            request_id=envelope.request_id,
            principal_id=envelope.principal_id,
            operation=envelope.operation,
            interaction_context=envelope.interaction_context,
            stage=envelope.stage,
            intent_digest=sha256(intent_material.encode()).hexdigest(),
            plan_digest=envelope.plan_digest,
            metadata=envelope.metadata,
        )

    @staticmethod
    def with_plan_digest(envelope: OrchestrationEnvelope, plan_material: str) -> OrchestrationEnvelope:
        if not isinstance(plan_material, str) or not plan_material.strip():
            raise ValueError("plan_material_required")
        if len(plan_material.encode()) > MAX_REFERENCE * 8:
            raise ValueError("plan_material_too_large")
        return OrchestrationEnvelope(
            request_id=envelope.request_id,
            principal_id=envelope.principal_id,
            operation=envelope.operation,
            interaction_context=envelope.interaction_context,
            stage=envelope.stage,
            intent_digest=envelope.intent_digest,
            plan_digest=sha256(plan_material.encode()).hexdigest(),
            metadata=envelope.metadata,
        )

    @staticmethod
    def digest(envelope: OrchestrationEnvelope) -> str:
        material = "|".join((
            envelope.request_id,
            envelope.principal_id,
            envelope.operation,
            envelope.interaction_context.context_id,
            envelope.stage.value,
            envelope.intent_digest,
            envelope.plan_digest,
            repr(envelope.metadata),
        ))
        return sha256(material.encode()).hexdigest()
