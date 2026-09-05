"""Threshold authorization primitives for high-risk NORYX7 operations."""
from __future__ import annotations

from dataclasses import dataclass

MAX_PARTIES = 32
MAX_ID = 256


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_ID:
        raise ValueError(f"invalid_{name}")
    return value


@dataclass(frozen=True)
class AuthorizationProof:
    action_id: str
    approvers: tuple[str, ...]
    threshold: int
    epoch: int

    def __post_init__(self) -> None:
        _id(self.action_id, "action_id")
        if not self.approvers or len(self.approvers) > MAX_PARTIES:
            raise ValueError("invalid_approvers")
        if len(set(self.approvers)) != len(self.approvers):
            raise ValueError("duplicate_approver")
        for party in self.approvers:
            _id(party, "approver")
        if not isinstance(self.threshold, int) or not 1 <= self.threshold <= len(self.approvers):
            raise ValueError("invalid_threshold")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise ValueError("invalid_epoch")


class ThresholdAuthorizer:
    """Requires explicit independent principals for privileged operations."""

    def __init__(self, *, required_threshold: int) -> None:
        if not isinstance(required_threshold, int) or required_threshold < 1 or required_threshold > MAX_PARTIES:
            raise ValueError("invalid_required_threshold")
        self._required = required_threshold

    @property
    def required_threshold(self) -> int:
        return self._required

    def verify(self, proof: AuthorizationProof, *, action_id: str, epoch: int) -> bool:
        return (
            proof.action_id == action_id
            and proof.epoch == epoch
            and proof.threshold >= self._required
            and len(proof.approvers) >= self._required
        )
