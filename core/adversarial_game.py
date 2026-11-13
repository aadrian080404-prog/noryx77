"""Bounded attacker/defender game over an abstract local security model.

This is a deterministic simulation kernel. It has no network, process, tool,
filesystem, or production-control adapter and cannot attack external systems.
Its scores are policy weights, not empirical probabilities or risk estimates.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class AttackerMove(str, Enum):
    REPLAY = "replay"
    TAMPER_EVIDENCE = "tamper_evidence"
    EXFILTRATE = "exfiltrate"
    DISRUPT = "disrupt"


class DefenderMove(str, Enum):
    ENABLE_REPLAY_GUARD = "enable_replay_guard"
    REVOKE_CREDENTIAL = "revoke_credential"
    ISOLATE = "isolate"
    VERIFY_EVIDENCE = "verify_evidence"
    RESTORE_CHECKPOINT = "restore_checkpoint"


@dataclass(frozen=True)
class AbstractSecurityState:
    credential_compromised: bool = False
    replay_protected: bool = False
    evidence_integrity: bool = True
    data_exposed: bool = False
    service_available: bool = True
    isolated: bool = False
    checkpoint_valid: bool = True

    def __post_init__(self) -> None:
        for name in (
            "credential_compromised", "replay_protected", "evidence_integrity",
            "data_exposed", "service_available", "isolated", "checkpoint_valid",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name}_must_be_bool")


@dataclass(frozen=True)
class GamePlan:
    first_defense: DefenderMove
    worst_case_score: int
    horizon: int
    evaluated_states: int


class BoundedAdversarialGame:
    """Solve a finite max-min game with a hard horizon and a fixed move set."""

    MAX_HORIZON = 8
    DEFENDER_MOVES = tuple(DefenderMove)
    ATTACKER_MOVES = tuple(AttackerMove)

    @staticmethod
    def _defend(state: AbstractSecurityState, move: DefenderMove) -> AbstractSecurityState:
        if move is DefenderMove.ENABLE_REPLAY_GUARD:
            return AbstractSecurityState(
                state.credential_compromised, True, state.evidence_integrity,
                state.data_exposed, state.service_available, state.isolated,
                state.checkpoint_valid,
            )
        if move is DefenderMove.REVOKE_CREDENTIAL:
            return AbstractSecurityState(
                False, state.replay_protected, state.evidence_integrity,
                state.data_exposed, state.service_available, state.isolated,
                state.checkpoint_valid,
            )
        if move is DefenderMove.ISOLATE:
            return AbstractSecurityState(
                state.credential_compromised, state.replay_protected,
                state.evidence_integrity, state.data_exposed, False, True,
                state.checkpoint_valid,
            )
        if move is DefenderMove.VERIFY_EVIDENCE:
            return AbstractSecurityState(
                state.credential_compromised, state.replay_protected,
                state.checkpoint_valid, state.data_exposed,
                state.service_available, state.isolated, state.checkpoint_valid,
            )
        if move is DefenderMove.RESTORE_CHECKPOINT:
            if not state.checkpoint_valid:
                return state
            return AbstractSecurityState(
                False, state.replay_protected, True, state.data_exposed,
                True, False, state.checkpoint_valid,
            )
        raise ValueError("unknown_defender_move")

    @staticmethod
    def _attack(state: AbstractSecurityState, move: AttackerMove) -> AbstractSecurityState:
        if move is AttackerMove.REPLAY:
            compromised = state.credential_compromised or not state.replay_protected
            return AbstractSecurityState(
                compromised, state.replay_protected, state.evidence_integrity,
                state.data_exposed, state.service_available, state.isolated,
                state.checkpoint_valid,
            )
        if move is AttackerMove.TAMPER_EVIDENCE:
            return AbstractSecurityState(
                state.credential_compromised, state.replay_protected, False,
                state.data_exposed, state.service_available, state.isolated,
                state.checkpoint_valid,
            )
        if move is AttackerMove.EXFILTRATE:
            exposed = state.data_exposed or (state.credential_compromised and not state.isolated)
            return AbstractSecurityState(
                state.credential_compromised, state.replay_protected,
                state.evidence_integrity, exposed, state.service_available,
                state.isolated, state.checkpoint_valid,
            )
        if move is AttackerMove.DISRUPT:
            available = state.service_available and state.isolated
            return AbstractSecurityState(
                state.credential_compromised, state.replay_protected,
                state.evidence_integrity, state.data_exposed, available,
                state.isolated, state.checkpoint_valid,
            )
        raise ValueError("unknown_attacker_move")

    @staticmethod
    def score(state: AbstractSecurityState) -> int:
        # Explicit deterministic policy weights; not calibrated probabilities.
        return (
            (100 if not state.data_exposed else -100)
            + (80 if state.evidence_integrity else -80)
            + (40 if state.service_available else -40)
            + (20 if not state.credential_compromised else -20)
            - (10 if state.isolated else 0)
        )

    def solve(self, state: AbstractSecurityState, *, horizon: int = 3) -> GamePlan:
        if not isinstance(state, AbstractSecurityState):
            raise TypeError("abstract_security_state_required")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= self.MAX_HORIZON:
            raise ValueError("invalid_game_horizon")

        @lru_cache(maxsize=None)
        def value(current: AbstractSecurityState, remaining: int) -> int:
            if remaining == 0:
                return self.score(current)
            best = None
            for defense in self.DEFENDER_MOVES:
                defended = self._defend(current, defense)
                worst = min(
                    value(self._attack(defended, attack), remaining - 1)
                    for attack in self.ATTACKER_MOVES
                )
                if best is None or worst > best:
                    best = worst
            return self.score(current) if best is None else best

        candidates: list[tuple[int, int, DefenderMove]] = []
        for index, defense in enumerate(self.DEFENDER_MOVES):
            defended = self._defend(state, defense)
            worst = min(
                value(self._attack(defended, attack), horizon - 1)
                for attack in self.ATTACKER_MOVES
            )
            candidates.append((worst, -index, defense))
        best_score, _, best_move = max(candidates)
        return GamePlan(best_move, best_score, horizon, value.cache_info().currsize)
