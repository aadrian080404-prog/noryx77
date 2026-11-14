"""Proposal-only self-improvement pipeline with external admission boundary."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ImprovementStage(str, Enum):
    OBSERVE = "observe"
    ANALYZE = "analyze"
    PROPOSE = "propose"
    SIMULATE = "simulate"
    TEST = "test"
    VERIFY = "verify"
    ADMITTED = "admitted"


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    target: str
    rationale: str
    patch_digest: str


class ImprovementPipeline:
    """Models improvement as staged evidence; proposals cannot self-authorize."""

    ORDER = (
        ImprovementStage.OBSERVE,
        ImprovementStage.ANALYZE,
        ImprovementStage.PROPOSE,
        ImprovementStage.SIMULATE,
        ImprovementStage.TEST,
        ImprovementStage.VERIFY,
    )

    def __init__(self) -> None:
        self._stage = ImprovementStage.OBSERVE

    @property
    def stage(self) -> ImprovementStage:
        return self._stage

    def advance(self, stage: ImprovementStage) -> None:
        if not isinstance(stage, ImprovementStage):
            raise TypeError("invalid_improvement_stage")
        current_index = self.ORDER.index(self._stage) if self._stage in self.ORDER else -1
        target_index = self.ORDER.index(stage) if stage in self.ORDER else -1
        if target_index != current_index + 1:
            raise PermissionError("invalid_improvement_transition")
        self._stage = stage

    def admit_external(self) -> None:
        if self._stage is not ImprovementStage.VERIFY:
            raise PermissionError("verified_proposal_required")
        self._stage = ImprovementStage.ADMITTED
