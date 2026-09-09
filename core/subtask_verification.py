from __future__ import annotations

from dataclasses import dataclass

from .contracts import AgentResult, VerificationResult
from .subtask_uif import SubtaskRouteSet


@dataclass(frozen=True)
class SubtaskEvidence:
    subtask_id: str
    agent_id: str
    output: str
    verified: bool


@dataclass(frozen=True)
class SubtaskVerificationGate:
    evidence: tuple[SubtaskEvidence, ...]
    verification: VerificationResult
    commit_eligible: bool


def verify_subtasks(route_set: SubtaskRouteSet, results: tuple[AgentResult, ...]) -> SubtaskVerificationGate:
    """Verify exact subtask coverage before any aggregate commit decision."""
    if not isinstance(route_set, SubtaskRouteSet) or not route_set.verification.is_well_formed() or not route_set.verification.valid:
        return SubtaskVerificationGate((), VerificationResult(False, "subtask_verification", "subtask_routes_invalid"), False)
    if not isinstance(results, tuple) or not results:
        return SubtaskVerificationGate((), VerificationResult(False, "subtask_verification", "subtask_results_missing"), False)
    expected = tuple(item.subtask_id for item in route_set.routes)
    if not expected or len(set(expected)) != len(expected):
        return SubtaskVerificationGate((), VerificationResult(False, "subtask_verification", "subtask_route_identity_invalid"), False)
    if len(results) != len(expected):
        return SubtaskVerificationGate((), VerificationResult(False, "subtask_verification", "subtask_result_coverage_mismatch"), False)

    evidence: list[SubtaskEvidence] = []
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, AgentResult) or not result.is_well_formed():
            return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "malformed_subtask_result"), False)
        if result.task_id not in expected or result.task_id in seen:
            return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "subtask_result_identity_invalid"), False)
        if result.status != "completed":
            return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "subtask_incomplete"), False)
        verified = result.verification is not None and result.verification.is_well_formed() and result.verification.valid and result.verification.stage == "agent_result"
        item = SubtaskEvidence(result.task_id, result.agent_id, str(result.output), verified)
        evidence.append(item)
        seen.add(result.task_id)
        if not verified:
            return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "subtask_unverified"), False)

    if tuple(item.subtask_id for item in evidence) != expected:
        return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "subtask_result_order_invalid"), False)
    if any(route.route_authority if hasattr(route, "route_authority") else False for route in route_set.routes):
        return SubtaskVerificationGate(tuple(evidence), VerificationResult(False, "subtask_verification", "subtask_routes_invalid"), False)
    return SubtaskVerificationGate(tuple(evidence), VerificationResult(True, "subtask_verification", "subtask_commit_gate_ok"), True)
