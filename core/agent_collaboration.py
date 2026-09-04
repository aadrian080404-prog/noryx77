from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from threading import Lock
from typing import Any

from .contracts import AgentResult, TaskSpec, VerificationResult


@dataclass(frozen=True)
class CollaborationEvidence:
    """Immutable, runtime/execution-bound evidence exchanged by two peer agents."""

    runtime_id: str
    execution_id: str
    task_id: str
    source_agent_id: str
    target_agent_id: str
    output_digest: str
    verification_digest: str
    target_output_digest: str
    target_verification_digest: str = ""
    challenge: str = ""
    revision: int = 0
    seal: str = ""
    previous_evidence_digest: str = ""

    def canonical_bytes(self) -> bytes:
        payload = {
            "runtime_id": self.runtime_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "output_digest": self.output_digest,
            "verification_digest": self.verification_digest,
            "target_output_digest": self.target_output_digest,
            "target_verification_digest": self.target_verification_digest,
            "challenge": self.challenge,
            "revision": self.revision,
            "previous_evidence_digest": self.previous_evidence_digest,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

    def is_well_formed(self) -> bool:
        fields = (self.runtime_id, self.execution_id, self.task_id, self.source_agent_id, self.target_agent_id, self.challenge)
        return (
            all(isinstance(value, str) and bool(value.strip()) and len(value.encode()) <= 256 for value in fields)
            and self.source_agent_id != self.target_agent_id
            and isinstance(self.revision, int) and not isinstance(self.revision, bool) and 0 <= self.revision <= 32
            and self._valid_digest(self.output_digest)
            and self._valid_digest(self.verification_digest)
            and self._valid_digest(self.target_output_digest)
            and self._valid_digest(self.target_verification_digest)
            and (not self.seal or self._valid_digest(self.seal))
            and (not self.previous_evidence_digest or self._valid_digest(self.previous_evidence_digest))
        )

    @staticmethod
    def _valid_digest(value: str) -> bool:
        if not isinstance(value, str) or len(value) != 64:
            return False
        try:
            int(value, 16)
            return True
        except ValueError:
            return False


class PeerCollaboration:
    """Bounded two-peer protocol: independent outputs, challenge, then admission."""

    _DOMAIN = b"NORYX7/peer-collaboration/v1/"
    _MAX_ADMITTED_EVIDENCE = 4096
    _MAX_CHAIN_EVIDENCE = 8192

    def __init__(self, runtime_id: str, execution_id: str, *, seal_key: bytes, max_rounds: int = 2):
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise ValueError("invalid runtime_id")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid execution_id")
        if not isinstance(seal_key, bytes) or len(seal_key) < 32:
            raise ValueError("seal_key must contain at least 32 bytes")
        if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or not 1 <= max_rounds <= 2:
            raise ValueError("max_rounds must be between 1 and 2")
        self.runtime_id = runtime_id
        self.execution_id = execution_id
        self._seal_key = bytes(seal_key)
        self.max_rounds = max_rounds
        self._admitted_evidence: set[str] = set()
        self._chain_evidence: dict[str, CollaborationEvidence] = {}
        self._admitted_lock = Lock()

    @staticmethod
    def _digest(value: Any) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True).encode()
        return sha256(encoded).hexdigest()

    def _evidence_id(self, evidence: CollaborationEvidence) -> str:
        return self._digest({"canonical": evidence.canonical_bytes().hex(), "seal": evidence.seal})

    def evidence(self, task: TaskSpec, source: AgentResult, target_agent_id: str, challenge: str, revision: int = 0, *, previous_evidence_digest: str = "", target_output: Any = None, target_verification: VerificationResult | None = None) -> CollaborationEvidence:
        if not isinstance(task, TaskSpec) or not task.is_well_formed(): raise ValueError("invalid_task")
        if task.execution_id != self.execution_id or not isinstance(source, AgentResult) or not source.is_well_formed(): raise ValueError("execution_identity_mismatch")
        if source.task_id != task.task_id or source.status != "completed": raise ValueError("invalid_source_result")
        if not isinstance(target_agent_id, str) or not target_agent_id.strip() or target_agent_id == source.agent_id: raise ValueError("invalid_peer_identity")
        if not isinstance(challenge, str) or not challenge.strip() or len(challenge.encode()) > 256: raise ValueError("invalid_challenge")
        if isinstance(revision, bool) or not isinstance(revision, int) or not 0 <= revision <= 32: raise ValueError("invalid_revision")
        if previous_evidence_digest and not CollaborationEvidence._valid_digest(previous_evidence_digest): raise ValueError("invalid_previous_evidence_digest")
        if revision == 0 and previous_evidence_digest: raise ValueError("unexpected_previous_evidence_digest")
        if revision > 0 and not previous_evidence_digest: raise ValueError("missing_previous_evidence_digest")
        verification = source.verification
        if not isinstance(verification, VerificationResult) or not verification.is_well_formed() or not verification.valid: raise ValueError("unverified_source_result")
        if not isinstance(target_verification, VerificationResult) or not target_verification.is_well_formed() or not target_verification.valid or target_verification.stage != "agent_result": raise ValueError("unverified_target_result")
        evidence = CollaborationEvidence(self.runtime_id, self.execution_id, task.task_id, source.agent_id, target_agent_id, self._digest(source.output), self._digest(verification), self._digest(target_output), self._digest(target_verification), challenge, revision, "", previous_evidence_digest)
        seal = hmac.new(self._seal_key, self._DOMAIN + evidence.canonical_bytes(), sha256).hexdigest()
        return CollaborationEvidence(**{**evidence.__dict__, "seal": seal})

    def verify_evidence(self, evidence: CollaborationEvidence, *, task: TaskSpec) -> bool:
        if not isinstance(evidence, CollaborationEvidence) or not evidence.is_well_formed(): return False
        if not isinstance(task, TaskSpec) or task.execution_id != self.execution_id: return False
        if evidence.runtime_id != self.runtime_id or evidence.execution_id != self.execution_id or evidence.task_id != task.task_id: return False
        if evidence.revision == 0 and evidence.previous_evidence_digest: return False
        if evidence.revision > 0:
            if not evidence.previous_evidence_digest: return False
            with self._admitted_lock:
                previous = self._chain_evidence.get(evidence.previous_evidence_digest)
                if previous is None or previous.revision + 1 != evidence.revision: return False
                if (previous.runtime_id != evidence.runtime_id or previous.execution_id != evidence.execution_id or previous.task_id != evidence.task_id or previous.source_agent_id != evidence.source_agent_id or previous.target_agent_id != evidence.target_agent_id): return False
                if previous.revision == 0 and previous.output_digest == previous.target_output_digest: return False
        expected = hmac.new(self._seal_key, self._DOMAIN + evidence.canonical_bytes(), sha256).hexdigest()
        return hmac.compare_digest(expected, evidence.seal)

    def admit_consensus(self, task: TaskSpec, first: AgentResult, second: AgentResult, evidence: CollaborationEvidence) -> VerificationResult:
        if not self.verify_evidence(evidence, task=task): return VerificationResult(False, "collaboration", "evidence_integrity_failure")
        if not isinstance(first, AgentResult) or not isinstance(second, AgentResult): return VerificationResult(False, "collaboration", "invalid_peer_result")
        if first.agent_id == second.agent_id: return VerificationResult(False, "collaboration", "peer_identity_not_independent")
        if first.task_id != task.task_id or second.task_id != task.task_id: return VerificationResult(False, "collaboration", "task_identity_mismatch")
        if first.execution_id != self.execution_id or second.execution_id != self.execution_id: return VerificationResult(False, "collaboration", "execution_identity_mismatch")
        for result in (first, second):
            if result.status != "completed" or not isinstance(result.verification, VerificationResult) or not result.verification.valid: return VerificationResult(False, "collaboration", "unverified_peer_result")
            if result.verification.stage != "agent_result": return VerificationResult(False, "collaboration", "verification_stage_mismatch")
        if evidence.source_agent_id != first.agent_id or evidence.target_agent_id != second.agent_id: return VerificationResult(False, "collaboration", "evidence_peer_mismatch")
        if evidence.output_digest != self._digest(first.output): return VerificationResult(False, "collaboration", "evidence_output_mismatch")
        if evidence.verification_digest != self._digest(first.verification): return VerificationResult(False, "collaboration", "evidence_verification_mismatch")
        if evidence.target_output_digest != self._digest(second.output): return VerificationResult(False, "collaboration", "evidence_target_output_mismatch")
        if evidence.target_verification_digest != self._digest(second.verification): return VerificationResult(False, "collaboration", "evidence_target_verification_mismatch")
        evidence_id = self._evidence_id(evidence)
        disagreement = self._digest(first.output) != self._digest(second.output)
        with self._admitted_lock:
            if evidence_id in self._chain_evidence: return VerificationResult(False, "collaboration", "evidence_replay_rejected")
            if len(self._chain_evidence) >= self._MAX_CHAIN_EVIDENCE: return VerificationResult(False, "collaboration", "evidence_chain_limit")
            self._chain_evidence[evidence_id] = evidence
            if disagreement: return VerificationResult(False, "collaboration", "peer_disagreement_requires_resolution")
            if len(self._admitted_evidence) >= self._MAX_ADMITTED_EVIDENCE: return VerificationResult(False, "collaboration", "evidence_admission_limit")
            self._admitted_evidence.add(evidence_id)
        return VerificationResult(True, "collaboration", "independent_peer_results_admitted")
