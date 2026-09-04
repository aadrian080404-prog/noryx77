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


class PeerExecutionCoordinator:
    """Execute two distinct peers independently, then admit only verified agreement."""

    def __init__(self, collaboration: PeerCollaboration):
        if not isinstance(collaboration, PeerCollaboration):
            raise ValueError("invalid_peer_collaboration")
        self.collaboration = collaboration

    def execute(
        self,
        task: TaskSpec,
        first_agent: Any,
        second_agent: Any,
        execute: Callable[[Any, TaskSpec], AgentResult],
    ) -> PeerExecution:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_task")
        if task.execution_id != self.collaboration.execution_id:
            raise PermissionError("execution_identity_mismatch")
        if first_agent is None or second_agent is None:
            raise ValueError("peer_agent_required")
        first_id = getattr(first_agent, "agent_id", "")
        second_id = getattr(second_agent, "agent_id", "")
        if not isinstance(first_id, str) or not first_id.strip() or not isinstance(second_id, str) or not second_id.strip():
            raise ValueError("invalid_peer_identity")
        if first_id == second_id:
            raise ValueError("peer_identity_not_independent")

        first = execute(first_agent, task)
        if not isinstance(first, AgentResult) or not first.is_well_formed():
            raise ValueError("malformed_first_result")
        if first.agent_id != first_id or first.execution_id != task.execution_id or first.task_id != task.task_id:
            raise PermissionError("first_result_identity_mismatch")
        if not isinstance(first.verification, VerificationResult) or not first.verification.valid:
            raise PermissionError("first_result_unverified")

        second = execute(second_agent, task)
        if not isinstance(second, AgentResult) or not second.is_well_formed():
            raise ValueError("malformed_second_result")
        if second.agent_id != second_id or second.execution_id != task.execution_id or second.task_id != task.task_id:
            raise PermissionError("second_result_identity_mismatch")
        if not isinstance(second.verification, VerificationResult) or not second.verification.valid:
            raise PermissionError("second_result_unverified")

        evidence = self.collaboration.evidence(
            task,
            first,
            second.agent_id,
            "independently challenge the peer output before consensus",
            revision=0,
        )
        collaboration = self.collaboration.admit_consensus(task, first, second, evidence)
        if not collaboration.valid:
            raise PermissionError(collaboration.reason)
        return PeerExecution(first, second, collaboration, evidence.output_digest)
