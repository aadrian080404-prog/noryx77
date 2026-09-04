from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any, Mapping


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= 256


@dataclass(frozen=True)
class CollaborationEvidence:
    runtime_id: str
    pair_id: str
    execution_id: str
    interaction_id: str
    source_agent_id: str
    target_agent_id: str
    event_type: str
    evidence_digest: str
    previous_digest: str = ""
    seal: str = ""

    def is_well_formed(self) -> bool:
        fields = (self.runtime_id, self.pair_id, self.execution_id, self.interaction_id,
                  self.source_agent_id, self.target_agent_id, self.event_type)
        return (
            all(_valid_id(v) for v in fields)
            and self.source_agent_id != self.target_agent_id
            and _valid_digest(self.evidence_digest)
            and (not self.previous_digest or _valid_digest(self.previous_digest))
            and _valid_digest(self.seal)
        )


def _valid_digest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


class AgentRelationshipStore:
    """Evidence-only relationship memory; learning is quarantined until explicitly admitted."""

    _DOMAIN = b"NORYX7/agent-relationship/v1/"

    def __init__(self, runtime_id: str, pair_id: str, key: bytes, *, max_events: int = 1024, max_quarantine: int = 256):
        if not _valid_id(runtime_id):
            raise ValueError("invalid runtime_id")
        if not _valid_id(pair_id):
            raise ValueError("invalid pair_id")
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("relationship key must contain at least 32 bytes")
        if isinstance(max_events, bool) or not isinstance(max_events, int) or not 1 <= max_events <= 100_000:
            raise ValueError("invalid max_events")
        if isinstance(max_quarantine, bool) or not isinstance(max_quarantine, int) or not 1 <= max_quarantine <= 10_000:
            raise ValueError("invalid max_quarantine")
        self.runtime_id, self.pair_id, self._key = runtime_id, pair_id, bytes(key)
        self.max_events, self.max_quarantine = max_events, max_quarantine
        self._events: list[CollaborationEvidence] = []
        self._quarantine: list[CollaborationEvidence] = []

    def _message(self, event: CollaborationEvidence) -> bytes:
        return self._DOMAIN + _canonical({
            "runtime_id": event.runtime_id, "pair_id": event.pair_id,
            "execution_id": event.execution_id, "interaction_id": event.interaction_id,
            "source_agent_id": event.source_agent_id, "target_agent_id": event.target_agent_id,
            "event_type": event.event_type, "evidence_digest": event.evidence_digest,
            "previous_digest": event.previous_digest,
        })

    def _quarantine_event(self, event: CollaborationEvidence) -> None:
        if len(self._quarantine) >= self.max_quarantine:
            del self._quarantine[0]
        self._quarantine.append(event)

    def _admit_verified(self, event: CollaborationEvidence) -> bool:
        if len(self._events) >= self.max_events:
            return False
        if any(e.interaction_id == event.interaction_id for e in self._events):
            return False
        self._events.append(event)
        return True

    def record(self, *, execution_id: str, interaction_id: str, source_agent_id: str,
               target_agent_id: str, event_type: str, evidence: Mapping[str, Any]) -> CollaborationEvidence:
        if not all(_valid_id(v) for v in (execution_id, interaction_id, source_agent_id, target_agent_id, event_type)):
            raise ValueError("invalid relationship identity")
        if source_agent_id == target_agent_id:
            raise ValueError("relationship peers must be distinct")
        if not isinstance(evidence, Mapping):
            raise ValueError("evidence must be a mapping")
        if len(self._events) >= self.max_events:
            raise RuntimeError("relationship event limit exceeded")
        previous = self._events[-1].seal if self._events else ""
        digest = _digest({"execution_id": execution_id, "interaction_id": interaction_id,
                          "source": source_agent_id, "target": target_agent_id,
                          "event": event_type, "evidence": dict(evidence)})
        unsigned = CollaborationEvidence(self.runtime_id, self.pair_id, execution_id, interaction_id,
                                         source_agent_id, target_agent_id, event_type, digest, previous, "")
        seal = hmac.new(self._key, self._message(unsigned), hashlib.sha256).hexdigest()
        event = CollaborationEvidence(
            runtime_id=unsigned.runtime_id, pair_id=unsigned.pair_id,
            execution_id=unsigned.execution_id, interaction_id=unsigned.interaction_id,
            source_agent_id=unsigned.source_agent_id, target_agent_id=unsigned.target_agent_id,
            event_type=unsigned.event_type, evidence_digest=unsigned.evidence_digest,
            previous_digest=unsigned.previous_digest, seal=seal,
        )
        self._events.append(event)
        return event

    def verify_evidence_payload(self, event: CollaborationEvidence, evidence: Mapping[str, Any]) -> bool:
        """Recompute the evidence digest when the original payload is available."""
        if not isinstance(event, CollaborationEvidence) or not event.is_well_formed() or not isinstance(evidence, Mapping):
            return False
        expected = _digest({"execution_id": event.execution_id, "interaction_id": event.interaction_id,
                            "source": event.source_agent_id, "target": event.target_agent_id,
                            "event": event.event_type, "evidence": dict(evidence)})
        return hmac.compare_digest(expected, event.evidence_digest) and self.verify(event)

    def verify(self, event: CollaborationEvidence) -> bool:
        if not isinstance(event, CollaborationEvidence) or not event.is_well_formed():
            return False
        if event.runtime_id != self.runtime_id or event.pair_id != self.pair_id:
            return False
        expected = hmac.new(self._key, self._message(event), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, event.seal)

    def admit(self, event: CollaborationEvidence) -> bool:
        if not isinstance(event, CollaborationEvidence) or not event.is_well_formed():
            return False
        if event.runtime_id != self.runtime_id or event.pair_id != self.pair_id:
            self._quarantine_event(event)
            return False
        expected_previous = self._events[-1].seal if self._events else ""
        if event.previous_digest != expected_previous:
            self._quarantine_event(event)
            return False
        if not self.verify(event):
            self._quarantine_event(event)
            return False
        return self._admit_verified(event)

    def snapshot(self) -> tuple[CollaborationEvidence, ...]:
        return tuple(self._events)

    def quarantined(self) -> tuple[CollaborationEvidence, ...]:
        return tuple(self._quarantine)

    def evidence_digest(self) -> str:
        return _digest(tuple(e.__dict__ for e in self._events))

    def relationship_facts(self) -> Mapping[str, Any]:
        """Returns evidence-derived facts, never an unconstrained trust score."""
        events = self._events
        return {
            "pair_id": self.pair_id,
            "runtime_id": self.runtime_id,
            "interactions": len(events),
            "verified_challenges": sum(e.event_type == "verified_challenge" for e in events),
            "successful_corrections": sum(e.event_type == "successful_correction" for e in events),
            "evidence_digest": self.evidence_digest(),
        }
