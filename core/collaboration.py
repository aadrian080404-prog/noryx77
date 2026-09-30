from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .contracts import AgentResult, TaskSpec, VerificationResult


@dataclass(frozen=True)
class Proposal:
    execution_id: str
    task_id: str
    agent_id: str
    output: str
    evidence_digest: str


@dataclass(frozen=True)
class Critique:
    execution_id: str
    task_id: str
    agent_id: str
    target_agent_id: str
    accepted: bool
    output: str
    evidence_digest: str


@dataclass(frozen=True)
class Reconciliation:
    execution_id: str
    task_id: str
    proposal_agent_id: str
    critic_agent_id: str
    accepted: bool
    output: str
    proposal_digest: str
    critique_digest: str


class AgentCollaboration:
    """Real bounded Primary -> Secondary -> Primary reasoning handshake.

    This is deliberately a reasoning protocol, not an authority channel. Both
    agents remain subject to the same runtime verification and authorization
    boundaries, and neither agent can grant itself execution authority.
    """

    def __init__(self, verifier: Any) -> None:
        self.verifier = verifier

    @staticmethod
    def _digest(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _review_task(task: TaskSpec, proposal: str, primary_id: str) -> TaskSpec:
        return TaskSpec(
            task_id=f"{task.task_id}:critique",
            task_type="agent_critique",
            objective=(
                "Cross-check the Primary proposal. Begin the response with exactly "
                "APPROVE or REJECT, then identify evidence, unsupported claims, risks, "
                "and concrete corrections. Never claim an external action was executed."
            ),
            input={"original_task": task.input, "proposal": proposal, "primary_agent_id": primary_id},
            constraints=task.constraints,
            verification_requirements=("structured_critique", "no_invented_evidence"),
            risk_class=task.risk_class,
            execution_id=task.execution_id,
        )

    @staticmethod
    def _revision_task(task: TaskSpec, proposal: str, critique: str, primary_id: str, secondary_id: str) -> TaskSpec:
        return TaskSpec(
            task_id=f"{task.task_id}:reconciliation",
            task_type="agent_reconciliation",
            objective=(
                "Reconcile the Primary proposal with the Secondary critique. Preserve "
                "supported content, correct supported issues, and explicitly state "
                "INSUFFICIENT_EVIDENCE where evidence is missing. Do not invent facts."
            ),
            input={
                "original_task": task.input,
                "proposal": proposal,
                "critique": critique,
                "primary_agent_id": primary_id,
                "secondary_agent_id": secondary_id,
            },
            constraints=task.constraints,
            verification_requirements=("reconciled_reasoning", "no_invented_evidence"),
            risk_class=task.risk_class,
            execution_id=task.execution_id,
        )

    def run(self, task: TaskSpec, primary: Any, secondary: Any) -> tuple[Reconciliation, VerificationResult]:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise ValueError("invalid_collaboration_task")
        if primary is None or secondary is None or primary is secondary:
            raise ValueError("distinct_agents_required")
        primary_id = getattr(primary, "agent_id", "")
        secondary_id = getattr(secondary, "agent_id", "")
        if not primary_id or not secondary_id or primary_id == secondary_id:
            raise ValueError("distinct_agent_ids_required")
        if not task.execution_id:
            raise ValueError("execution_id_required")

        proposal_result: AgentResult = primary.run(task)
        if not isinstance(proposal_result, AgentResult) or proposal_result.execution_id != task.execution_id:
            raise RuntimeError("proposal_execution_identity_mismatch")
        proposal_check = proposal_result.verification
        if proposal_result.status != "completed" or not isinstance(proposal_check, VerificationResult) or not proposal_check.valid:
            raise RuntimeError("proposal_not_verified")
        proposal_output = proposal_result.output
        if not isinstance(proposal_output, str) or not proposal_output.strip():
            raise RuntimeError("proposal_output_missing")
        proposal = Proposal(task.execution_id, task.task_id, primary_id, proposal_output.strip(), self._digest(proposal_output.strip()))

        critique_task = self._review_task(task, proposal.output, primary_id)
        critique_result: AgentResult = secondary.run(critique_task)
        if not isinstance(critique_result, AgentResult) or critique_result.execution_id != task.execution_id:
            raise RuntimeError("critique_execution_identity_mismatch")
        critique_check = critique_result.verification
        if critique_result.status != "completed" or not isinstance(critique_check, VerificationResult) or not critique_check.valid:
            raise RuntimeError("critique_not_verified")
        critique_output = critique_result.output
        if not isinstance(critique_output, str) or not critique_output.strip():
            raise RuntimeError("critique_output_missing")
        normalized = critique_output.strip()

        # Real LLM providers may prepend harmless Markdown formatting
        # (for example "## APPROVE") while still providing an explicit
        # machine-readable verdict. Accept only an explicit verdict on the
        # first non-empty line; never infer approval from free-form prose.
        first_line = next(
            (line.strip() for line in normalized.splitlines() if line.strip()),
            "",
        )
        verdict_token = first_line.lstrip("#>*` ").split(None, 1)[0]
        verdict_token = verdict_token.rstrip(":,;.!?").upper()

        if verdict_token not in {"APPROVE", "REJECT"}:
            raise RuntimeError("unstructured_critique")
        critique = Critique(
            task.execution_id,
            task.task_id,
            secondary_id,
            primary_id,
            verdict_token == "APPROVE",
            normalized,
            self._digest(normalized),
        )

        revision_task = self._revision_task(task, proposal.output, critique.output, primary_id, secondary_id)
        reconciliation_result: AgentResult = primary.run(revision_task)
        if not isinstance(reconciliation_result, AgentResult) or reconciliation_result.execution_id != task.execution_id:
            raise RuntimeError("reconciliation_execution_identity_mismatch")
        reconciliation_check = reconciliation_result.verification
        if reconciliation_result.status != "completed" or not isinstance(reconciliation_check, VerificationResult) or not reconciliation_check.valid:
            raise RuntimeError("reconciliation_not_verified")
        output = reconciliation_result.output
        if not isinstance(output, str) or not output.strip():
            raise RuntimeError("reconciliation_output_missing")
        final_check = self.verifier.verify_output(output.strip(), stage="collaboration")
        if not isinstance(final_check, VerificationResult) or not final_check.is_well_formed() or not final_check.valid:
            raise RuntimeError("collaboration_output_not_verified")

        reconciliation = Reconciliation(
            task.execution_id,
            task.task_id,
            primary_id,
            secondary_id,
            True,
            output.strip(),
            proposal.evidence_digest,
            critique.evidence_digest,
        )
        return reconciliation, VerificationResult(
            True,
            "collaboration",
            "proposal_critique_reconciled",
            details=(primary_id, secondary_id, proposal.evidence_digest, critique.evidence_digest),
        )
