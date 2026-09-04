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


def _valid_digest(value: str, *, allow_empty: bool = False) -> bool:
    if allow_empty and value == "":
        return True
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


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
            all(isinstance(v, str) and bool(v.strip()) and len(v.encode("utf-8")) <= 256 for v in fields)
            and _valid_digest(self.evidence_digest)
            and _valid_digest(self.previous_digest, allow_empty=True)
            and _valid_digest(self.seal)
        )


class AgentRelationshipStore:
    """Evidence-only relationship memory; learning is quarantined until explicitly admitted."""

    _DOMAIN = b"NORYX7/agent-relationship/v1/"
    _MAX_EVENTS = 4096
    _MAX_QUARANTINE = 1024

    def __init__(self, runtime_id: str, pair_id: str, key: bytes, max_events: int | None = None, max_quarantine: int | None = None):
        if not isinstance(runtime_id, str) or not runtime_id.strip() or len(runtime_id.encode("utf-8")) > 256:
            raise ValueError("invalid runtime_id")
        if not isinstance(pair_id, str) or not pair_id.strip() or len(pair_id.encode("utf-8")) > 256:
            raise ValueError("invalid pair_id")
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("relationship key must contain at least 32 bytes")
        if max_events is not None and (isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 1):
            raise ValueError("max_events must be a positive integer")
        if max_quarantine is not None and (isinstance(max_quarantine, bool) or not isinstance(max_quarantine, int) or max_quarantine < 1):
            raise ValueError("max_quarantine must be a positive integer")
        self.runtime_id, self.pair_id, self._key = runtime_id, pair_id, bytes(key)
        self._max_events = max_events if max_events is not None else self._MAX_EVENTS
        self._max_quarantine = max_quarantine if max_quarantine is not None else self._MAX_QUARANTINE
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

    @staticmethod
    def _event_digest(*, execution_id: str, interaction_id: str, source_agent_id: str,
                      target_agent_id: str, event_type: str, evidence: Mapping[str, Any]) -> str:
        return _digest({"execution_id": execution_id, "interaction_id": interaction_id,
                        "source": source_agent_id, "target": target_agent_id,
                        "event": event_type, "evidence": dict(evidence)})

    def _quarantine_event(self, event: CollaborationEvidence) -> None:
        if len(self._quarantine) >= self._max_quarantine:
            self._quarantine.pop(0)
        self._quarantine.append(event)

    def record(self, *, execution_id: str, interaction_id: str, source_agent_id: str,
               target_agent_id: str, event_type: str, evidence: Mapping[str, Any]) -> CollaborationEvidence:
        fields = (execution_id, interaction_id, source_agent_id, target_agent_id, event_type)
        if not all(isinstance(v, str) and bool(v.strip()) and len(v.encode("utf-8")) <= 256 for v in fields):
            raise ValueError("invalid relationship identity")
        if source_agent_id == target_agent_id:
            raise ValueError("relationship peers must be distinct")
        if not isinstance(evidence, Mapping):
            raise ValueError("evidence must be a mapping")
        if len(self._events) >= self._max_events:
            raise RuntimeError("relationship history limit exceeded")
        if any(e.interaction_id == interaction_id for e in self._events):
            raise ValueError("duplicate relationship interaction")
        previous = self._events[-1].seal if self._events else ""
        digest = self._event_digest(execution_id=execution_id, interaction_id=interaction_id,
                                    source_agent_id=source_agent_id, target_agent_id=target_agent_id,
                                    event_type=event_type, evidence=evidence)
        unsigned = CollaborationEvidence(self.runtime_id, self.pair_id, execution_id, interaction_id,
                                         source_agent_id, target_agent_id, event_type, digest, previous, "")
        seal = hmac.new(self._key, self._message(unsigned), hashlib.sha256).hexdigest()
        event = CollaborationEvidence(self.runtime_id, self.pair_id, execution_id, interaction_id,
                                      source_agent_id, target_agent_id, event_type, digest, previous, seal)
        self._events.append(event)
        return event

    def verify_evidence_payload(self, event: CollaborationEvidence, evidence: Mapping[str, Any]) -> bool:
        if not isinstance(event, CollaborationEvidence) or not isinstance(evidence, Mapping) or not event.is_well_formed():
            return False
        expected = self._event_digest(execution_id=event.execution_id, interaction_id=event.interaction_id,
                                      source_agent_id=event.source_agent_id, target_agent_id=event.target_agent_id,
                                      event_type=event.event_type, evidence=evidence)
        return hmac.compare_digest(expected, event.evidence_digest)

    def admit(self, event: CollaborationEvidence) -> bool:
        if not isinstance(event, CollaborationEvidence) or not event.is_well_formed():
            if isinstance(event, CollaborationEvidence): self._quarantine_event(event)
            return False
        if event.runtime_id != self.runtime_id or event.pair_id != self.pair_id:
            self._quarantine_event(event)
            return False
        if event.source_agent_id == event.target_agent_id:
            self._quarantine_event(event)
            return False
        expected = hmac.new(self._key, self._message(event), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, event.seal):
            self._quarantine_event(event)
            return False
        if any(e.interaction_id == event.interaction_id for e in self._events):
            return False
        expected_previous = self._events[-1].seal if self._events else ""
        if event.previous_digest != expected_previous:
            self._quarantine_event(event)
            return False
        if len(self._events) >= self._max_events:
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
        events = self._events
        return {
            "pair_id": self.pair_id,
            "runtime_id": self.runtime_id,
            "interactions": len(events),
            "verified_challenges": sum(e.event_type == "verified_challenge" for e in events),
            "successful_corrections": sum(e.event_type == "successful_correction" for e in events),
            "evidence_digest": self.evidence_digest(),
        }
