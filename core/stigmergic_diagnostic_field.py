"""Stigmergic diagnostic field: proposals, evidence traces, and emergent review.

This is a coordination primitive, not an authorization system. A corroborated
claim is still only a hypothesis; callers must route every consequential action
through NORYX7's ordinary local policy and ActionGate.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from threading import RLock
import time
from typing import Callable


@dataclass(frozen=True)
class DiagnosticTrace:
    claim_id: str
    principal_id: str
    agent_id: str
    evidence_id: str
    evidence_fingerprint: str
    polarity: int
    strength: float
    issued_at: float
    expires_at: float
    signature: str


@dataclass(frozen=True)
class DiagnosticConsensus:
    claim_id: str
    status: str
    positive_principals: int
    negative_principals: int
    positive_weight: float
    negative_weight: float
    confidence: float
    active_traces: int
    evaluated_at: float


class StigmergicDiagnosticField:
    """Append-only, expiring evidence field with principal-level independence.

    The verifier must validate each trace's signature against the configured
    federation trust/revocation state. Agents are not independent voters:
    only one latest active trace per principal contributes to a claim.
    """

    MAX_TEXT_BYTES = 256
    MAX_TTL_SECONDS = 86_400.0
    MAX_TRACES = 100_000

    def __init__(
        self,
        verifier: Callable[[DiagnosticTrace], bool],
        *,
        clock: Callable[[], float] = time.time,
        half_life_seconds: float = 900.0,
        minimum_principals: int = 3,
        corroboration_threshold: float = 0.60,
        rejection_threshold: float = 0.60,
        minimum_margin: float = 0.20,
        max_traces: int = 10_000,
    ) -> None:
        if not callable(verifier) or not callable(clock):
            raise TypeError("verifier_and_clock_required")
        if (isinstance(half_life_seconds, bool)
                or not isinstance(half_life_seconds, (int, float))
                or not math.isfinite(float(half_life_seconds))
                or half_life_seconds <= 0):
            raise ValueError("positive_finite_half_life_required")
        if (isinstance(minimum_principals, bool)
                or not isinstance(minimum_principals, int)
                or minimum_principals < 2):
            raise ValueError("minimum_principals_must_be_at_least_two")
        for name, value in (("corroboration_threshold", corroboration_threshold),
                            ("rejection_threshold", rejection_threshold),
                            ("minimum_margin", minimum_margin)):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value)) or not 0 < value <= 1):
                raise ValueError(f"invalid_{name}")
        if isinstance(max_traces, bool) or not isinstance(max_traces, int) or not 1 <= max_traces <= self.MAX_TRACES:
            raise ValueError("invalid_max_traces")
        self._verifier = verifier
        self._clock = clock
        self._half_life = float(half_life_seconds)
        self._minimum_principals = minimum_principals
        self._corroboration_threshold = float(corroboration_threshold)
        self._rejection_threshold = float(rejection_threshold)
        self._minimum_margin = float(minimum_margin)
        self._max_traces = max_traces
        self._traces: dict[str, list[DiagnosticTrace]] = {}
        self._seen_evidence: set[tuple[str, str, str]] = set()
        self._lock = RLock()

    @classmethod
    def _valid_text(cls, value: str) -> bool:
        return (isinstance(value, str) and bool(value.strip())
                and len(value.encode("utf-8")) <= cls.MAX_TEXT_BYTES)

    @staticmethod
    def _valid_fingerprint(value: str) -> bool:
        if not isinstance(value, str) or len(value) != 64:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
        return True

    @staticmethod
    def claim_fingerprint(namespace: str, subject: str) -> str:
        """Return a stable opaque claim key; do not put raw secrets in a claim."""
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("claim_namespace_required")
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("claim_subject_required")
        payload = (namespace.strip() + "\0" + subject.strip()).encode("utf-8")
        return sha256(payload).hexdigest()

    def submit(self, trace: DiagnosticTrace) -> bool:
        if not isinstance(trace, DiagnosticTrace):
            return False
        if not all(self._valid_text(x) for x in (
            trace.claim_id, trace.principal_id, trace.agent_id,
            trace.evidence_id, trace.signature
        )):
            return False
        if not self._valid_fingerprint(trace.evidence_fingerprint):
            return False
        if isinstance(trace.polarity, bool) or trace.polarity not in (-1, 1):
            return False
        if (isinstance(trace.strength, bool)
                or not isinstance(trace.strength, (int, float))
                or not math.isfinite(float(trace.strength))
                or not 0.0 < trace.strength <= 1.0):
            return False
        if any(isinstance(x, bool) or not isinstance(x, (int, float))
               or not math.isfinite(float(x))
               for x in (trace.issued_at, trace.expires_at)):
            return False
        ttl = float(trace.expires_at) - float(trace.issued_at)
        if ttl <= 0 or ttl > self.MAX_TTL_SECONDS:
            return False
        try:
            now = float(self._clock())
        except Exception:
            return False
        if not math.isfinite(now) or trace.issued_at > now + 30 or trace.expires_at <= now:
            return False
        try:
            verified = self._verifier(trace)
        except Exception:
            return False
        if verified is not True:
            return False

        dedupe_key = (trace.claim_id, trace.principal_id, trace.evidence_id)
        with self._lock:
            if dedupe_key in self._seen_evidence:
                return False
            count = sum(len(items) for items in self._traces.values())
            if count >= self._max_traces:
                return False
            self._seen_evidence.add(dedupe_key)
            self._traces.setdefault(trace.claim_id, []).append(trace)
            return True

    def evaluate(self, claim_id: str) -> DiagnosticConsensus:
        if not self._valid_text(claim_id):
            raise ValueError("valid_claim_id_required")
        try:
            now = float(self._clock())
        except Exception:
            raise RuntimeError("diagnostic_clock_unavailable") from None
        if not math.isfinite(now):
            raise RuntimeError("diagnostic_clock_invalid")

        with self._lock:
            history = tuple(self._traces.get(claim_id, ()))

        # Keep the newest active observation per principal. Multiple agents
        # under one principal cannot manufacture quorum by multiplying votes.
        latest: dict[str, DiagnosticTrace] = {}
        for trace in history:
            if trace.issued_at <= now + 30 and trace.expires_at > now:
                current = latest.get(trace.principal_id)
                if current is None or trace.issued_at > current.issued_at:
                    latest[trace.principal_id] = trace

        positive = negative = 0
        positive_weight = negative_weight = 0.0
        for trace in latest.values():
            age = max(0.0, now - float(trace.issued_at))
            decay = math.pow(0.5, age / self._half_life)
            weight = float(trace.strength) * decay
            if trace.polarity > 0:
                positive += 1
                positive_weight += weight
            else:
                negative += 1
                negative_weight += weight

        total = positive_weight + negative_weight
        confidence = max(positive_weight, negative_weight) / total if total else 0.0
        status = "insufficient_evidence"
        enough_independent = len(latest) >= self._minimum_principals
        if enough_independent and total > 0:
            margin = abs(positive_weight - negative_weight) / total
            if positive_weight / total >= self._corroboration_threshold and margin >= self._minimum_margin:
                status = "corroborated"
            elif negative_weight / total >= self._rejection_threshold and margin >= self._minimum_margin:
                status = "challenged"
            elif positive_weight > 0 and negative_weight > 0:
                status = "contested"

        return DiagnosticConsensus(
            claim_id=claim_id,
            status=status,
            positive_principals=positive,
            negative_principals=negative,
            positive_weight=positive_weight,
            negative_weight=negative_weight,
            confidence=confidence,
            active_traces=len(latest),
            evaluated_at=now,
        )

    def trace_count(self, claim_id: str | None = None) -> int:
        with self._lock:
            if claim_id is not None:
                return len(self._traces.get(claim_id, ()))
            return sum(len(items) for items in self._traces.values())
