from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .agent_collaboration import PeerCollaboration
from .contracts import AgentResult, TaskSpec, VerificationResult


@dataclass(frozen=True)
class PeerExecution:
    first: AgentResult
    second: AgentResult
    collaboration: VerificationResult
    evidence_digest: str


@dataclass(frozen=True)
class PeerChallenge:
    """A bounded, explicit peer revision produced after an initial disagreement."""

    first: AgentResult
    second: AgentResult
    challenge: str


class PeerExecutionCoordinator:
    """Execute two peers independently, then resolve disagreement through bounded revision."""

    def __init__(self, collaboration: PeerCollaboration):
        if not isinstance(collaboration, PeerCollaboration):
            raise ValueError("invalid_peer_collaboration")
        self.collaboration = collaboration

    @staticmethod
    def _validate_result(result: Any, expected_agent_id: str, task: TaskSpec, prefix: str) -> AgentResult:
        if not isinstance(result, AgentResult) or not result.is_well_formed():
            raise ValueError(f"malformed_{prefix}_result")
        if result.agent_id != expected_agent_id or result.execution_id != task.execution_id or result.task_id != task.task_id:
            raise PermissionError(f"{prefix}_result_identity_mismatch")
        if result.status != "completed" or not isinstance(result.verification, VerificationResult) or not result.verification.valid:
            raise PermissionError(f"{prefix}_result_unverified")
        if result.verification.stage != "agent_result":
            raise PermissionError(f"{prefix}_verification_stage_mismatch")
        return result

    def execute(
        self,
        task: TaskSpec,
        first_agent: Any,
        second_agent: Any,
        execute: Callable[[Any, TaskSpec], AgentResult],
        *,
        challenge: Callable[[TaskSpec, AgentResult, AgentResult, int], PeerChallenge] | None = None,
    ) -> PeerExecution:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        if task.execution_id != self.collaboration.execution_id:
            raise PermissionError("execution_identity_mismatch")
        if not callable(execute):
            raise ValueError("invalid_peer_executor")
        if first_agent is None or second_agent is None:
            raise ValueError("peer_agent_required")
        first_id, second_id = getattr(first_agent, "agent_id", ""), getattr(second_agent, "agent_id", "")
        if not isinstance(first_id, str) or not first_id.strip() or not isinstance(second_id, str) or not second_id.strip():
            raise ValueError("invalid_peer_identity")
        if first_id == second_id:
            raise ValueError("peer_identity_not_independent")
        if challenge is not None and not callable(challenge):
            raise ValueError("invalid_peer_challenge")

        first = self._validate_result(execute(first_agent, task), first_id, task, "first")
        second = self._validate_result(execute(second_agent, task), second_id, task, "second")
        evidence = self.collaboration.evidence(
            task,
            first,
            second.agent_id,
            "independently challenge the peer output before consensus",
            revision=0,
            target_output=second.output,
            target_verification=second.verification,
        )
        collaboration = self.collaboration.admit_consensus(task, first, second, evidence)
        if collaboration.valid:
            return PeerExecution(first, second, collaboration, self.collaboration.evidence_digest(evidence))
        if collaboration.reason != "peer_disagreement_requires_resolution" or challenge is None:
            raise PermissionError(collaboration.reason)

        previous_digest = self.collaboration.evidence_digest(evidence)
        current_first, current_second = first, second
        for revision in range(1, self.collaboration.max_rounds + 1):
            proposed = challenge(task, current_first, current_second, revision)
            if (
                not isinstance(proposed, PeerChallenge)
                or not isinstance(proposed.challenge, str)
                or not proposed.challenge.strip()
                or len(proposed.challenge.encode()) > 256
            ):
                raise ValueError("invalid_peer_challenge")
            current_first = self._validate_result(proposed.first, first_id, task, "first_revision")
            current_second = self._validate_result(proposed.second, second_id, task, "second_revision")
            evidence = self.collaboration.evidence(
                task,
                current_first,
                current_second.agent_id,
                proposed.challenge,
                revision=revision,
                previous_evidence_digest=previous_digest,
                target_output=current_second.output,
                target_verification=current_second.verification,
            )
            collaboration = self.collaboration.admit_consensus(task, current_first, current_second, evidence)
            if collaboration.valid:
                return PeerExecution(current_first, current_second, collaboration, self.collaboration.evidence_digest(evidence))
            if collaboration.reason != "peer_disagreement_requires_resolution":
                raise PermissionError(collaboration.reason)
            previous_digest = self.collaboration.evidence_digest(evidence)
        raise PermissionError("peer_disagreement_unresolved")
