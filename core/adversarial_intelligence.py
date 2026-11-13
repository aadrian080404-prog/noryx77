"""Bounded, evidence-first adversarial cognition contracts.

The implementation is a deterministic simulation scaffold. It has no network,
process, filesystem, or production-control adapter and cannot attack live systems.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable


class Verdict(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    digest: str
    verified: bool
    independent: bool


@dataclass(frozen=True)
class DefensiveProposal:
    proposal_id: str
    action: str
    scope: str
    reversible: bool
    requires_human_approval: bool


@dataclass(frozen=True)
class JuryDecision:
    verdict: Verdict
    reasons: tuple[str, ...]
    reviewer_ids: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedOutcome:
    scenario_id: str
    proposal_id: str
    succeeded: bool
    evidence: tuple[Evidence, ...]


class IndependentJury:
    """Two deliberately different deterministic reviewers; disagreement is inconclusive."""

    REVIEWERS = ("evidence_integrity_reviewer", "scope_safety_reviewer")

    @staticmethod
    def _valid_evidence(evidence: tuple[Evidence, ...]) -> bool:
        if not evidence or any(not isinstance(item, Evidence) for item in evidence):
            return False
        if any(not item.verified or not item.independent for item in evidence):
            return False
        if any(not isinstance(item.digest, str) or len(item.digest) != 64 for item in evidence):
            return False
        return len({item.source_id for item in evidence}) >= 2

    def adjudicate(self, proposal: DefensiveProposal, evidence: tuple[Evidence, ...]) -> JuryDecision:
        if not isinstance(proposal, DefensiveProposal):
            return JuryDecision(Verdict.REJECT, ("invalid_proposal",), self.REVIEWERS)
        integrity_ok = self._valid_evidence(evidence)
        scope_ok = (
            isinstance(proposal.scope, str) and bool(proposal.scope.strip())
            and isinstance(proposal.action, str) and bool(proposal.action.strip())
            and proposal.reversible
        )
        # High-impact actions are never approved by this simulation jury.
        if proposal.requires_human_approval:
            scope_ok = False
        votes = (integrity_ok, scope_ok)
        if votes[0] and votes[1]:
            return JuryDecision(Verdict.ACCEPT, ("independent_evidence_and_reversible_scope",), self.REVIEWERS)
        if not votes[0] and not votes[1]:
            return JuryDecision(Verdict.REJECT, ("evidence_and_scope_requirements_failed",), self.REVIEWERS)
        return JuryDecision(Verdict.INCONCLUSIVE, ("reviewers_disagree",), self.REVIEWERS)


class AnchoredBipolicy:
    """Keeps an immutable reference-policy digest beside a separately versioned candidate."""

    def __init__(self, reference_policy: dict[str, str], candidate_policy: dict[str, str]) -> None:
        self._reference = self._canonical_policy(reference_policy)
        self._reference_digest = hashlib.sha256(self._reference.encode()).hexdigest()
        self._candidate = self._canonical_policy(candidate_policy)
        self.candidate_version = 1

    @staticmethod
    def _canonical_policy(policy: dict[str, str]) -> str:
        if not isinstance(policy, dict) or not policy:
            raise ValueError("policy_must_be_nonempty_mapping")
        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in policy.items()):
            raise ValueError("invalid_policy_entry")
        return json.dumps(policy, sort_keys=True, separators=(",", ":"))

    @property
    def reference_digest(self) -> str:
        return self._reference_digest

    @property
    def reference_policy(self) -> dict[str, str]:
        return json.loads(self._reference)

    @property
    def candidate_policy(self) -> dict[str, str]:
        return json.loads(self._candidate)

    def update_candidate(self, policy: dict[str, str]) -> None:
        self._candidate = self._canonical_policy(policy)
        self.candidate_version += 1

    def reference_intact(self) -> bool:
        return hashlib.sha256(self._reference.encode()).hexdigest() == self._reference_digest


class MetaMorphSES:
    """Bounded meta-adjustment from verified outcomes only; no autonomous model training."""

    def __init__(self, *, threshold: int = 3, minimum: int = 1, maximum: int = 10) -> None:
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (threshold, minimum, maximum)):
            raise ValueError("integer_bounds_required")
        if minimum < 0 or maximum < minimum or not minimum <= threshold <= maximum:
            raise ValueError("invalid_meta_bounds")
        self.threshold, self.minimum, self.maximum = threshold, minimum, maximum
        self.successes = 0
        self.failures = 0

    def learn(self, outcome: VerifiedOutcome) -> int:
        if not isinstance(outcome, VerifiedOutcome) or not outcome.scenario_id or not outcome.proposal_id:
            raise ValueError("invalid_verified_outcome")
        if not outcome.evidence or any(not item.verified for item in outcome.evidence):
            raise PermissionError("unverified_learning_evidence")
        if outcome.succeeded:
            self.successes += 1
            self.threshold = max(self.minimum, self.threshold - 1)
        else:
            self.failures += 1
            self.threshold = min(self.maximum, self.threshold + 1)
        return self.threshold


class AdversarialTwin:
    """SEAT-like bounded twin that learns from both verified attacks and defenses."""

    def __init__(self, *, seed: int = 0, max_rounds: int = 64) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("invalid_seed")
        if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or not 1 <= max_rounds <= 256:
            raise ValueError("invalid_max_rounds")
        self.seed = seed
        self.max_rounds = max_rounds
        self.meta = MetaMorphSES()

    def scenario_id(self, round_index: int) -> str:
        if isinstance(round_index, bool) or not isinstance(round_index, int) or not 0 <= round_index < self.max_rounds:
            raise IndexError("round_out_of_bounds")
        return hashlib.sha256(f"{self.seed}:{round_index}:NORYX7_SIM".encode()).hexdigest()[:24]

    def learn(self, outcome: VerifiedOutcome) -> int:
        return self.meta.learn(outcome)


class SelfPlaySimulator:
    """Abstract zero-side-effect attacker/defender self-play with strict round limits."""

    def __init__(self, *, max_rounds: int = 32) -> None:
        if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or not 1 <= max_rounds <= 128:
            raise ValueError("invalid_self_play_limit")
        self.max_rounds = max_rounds

    def run(self, attacker_moves: Iterable[str], defender_moves: Iterable[str]) -> tuple[tuple[str, str], ...]:
        attacks, defenses = tuple(attacker_moves), tuple(defender_moves)
        if len(attacks) != len(defenses) or len(attacks) > self.max_rounds:
            raise ValueError("self_play_round_mismatch_or_limit")
        if any(not isinstance(x, str) or not x for x in attacks + defenses):
            raise ValueError("invalid_self_play_move")
        return tuple(zip(attacks, defenses))
