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
        return all(isinstance(v, str) and bool(v.strip()) and len(v.encode("utf-8")) <= 256 for v in fields) \
            and isinstance(self.evidence_digest, str) and len(self.evidence_digest) == 64 \
            and all(c in "0123456789abcdef" for c in self.evidence_digest) \
            and isinstance(self.previous_digest, str) \
            and (not self.previous_digest or (len(self.previous_digest) == 64 and all(c in "0123456789abcdef" for c in self.previous_digest))) \
            and isinstance(self.seal, str) and len(self.seal) == 64 and all(c in "0123456789abcdef" for c in self.seal)


class AgentRelationshipStore:
    """Evidence-only relationship memory; learning is quarantined until explicitly admitted."""

    _DOMAIN = b"NORYX7/agent-relationship/v1/"

    def __init__(self, runtime_id: str, pair_id: str, key: bytes):
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise ValueError("invalid runtime_id")
        if not isinstance(pair_id, str) or not pair_id.strip():
            raise ValueError("invalid pair_id")
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("relationship key must contain at least 32 bytes")
        self.runtime_id, self.pair_id, self._key = runtime_id, pair_id, bytes(key)
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

    def record(self, *, execution_id: str, interaction_id: str, source_agent_id: str,
               target_agent_id: str, event_type: str, evidence: Mapping[str, Any]) -> CollaborationEvidence:
        previous = self._events[-1].seal if self._events else ""
        digest = _digest({"execution_id": execution_id, "interaction_id": interaction_id,
                          "source": source_agent_id, "target": target_agent_id,
                          "event": event_type, "evidence": dict(evidence)})
        unsigned = CollaborationEvidence(self.runtime_id, self.pair_id, execution_id, interaction_id,
                                         source_agent_id, target_agent_id, event_type, digest, previous, "")
        seal = hmac.new(self._key, self._message(unsigned), hashlib.sha256).hexdigest()
        event = CollaborationEvidence(*unsigned.__dict__.values(), seal)
        self._events.append(event)
        return event

    def admit(self, event: CollaborationEvidence) -> bool:
        if not isinstance(event, CollaborationEvidence) or not event.is_well_formed():
            return False
        if event.runtime_id != self.runtime_id or event.pair_id != self.pair_id:
            return False
        expected_previous = self._events[-1].seal if self._events else ""
        if event.previous_digest != expected_previous:
            self._quarantine.append(event)
            return False
        expected = hmac.new(self._key, self._message(event), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, event.seal):
            self._quarantine.append(event)
            return False
        if any(e.interaction_id == event.interaction_id for e in self._events):
            return False
        self._events.append(event)
        return True

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
