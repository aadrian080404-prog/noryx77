from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Any

@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event: str
    principal_id: str
    timestamp: float
    previous_digest: str
    digest: str
    details: tuple[tuple[str, str], ...] = ()

class AuditLog:
    """Append-only hash-chained audit log with integrity-protected details."""
    def __init__(self):
        self._events = []
        self._head = "0" * 64

    @property
    def events(self): return tuple(self._events)
    @property
    def head(self): return self._head

    @staticmethod
    def _normalize_details(details: dict[str, Any]) -> tuple[tuple[str, str], ...]:
        if not isinstance(details, dict): raise TypeError("audit_details_must_be_mapping")
        normalized = []
        for key, value in sorted(details.items(), key=lambda item: str(item[0])):
            if not isinstance(key, str) or not key.strip(): raise ValueError("invalid_audit_detail_key")
            text = str(value)
            if len(text) > 2048: raise ValueError("audit_detail_too_large")
            normalized.append((key, text))
        return tuple(normalized)

    @staticmethod
    def _digest(sequence: int, event: str, principal_id: str, timestamp: float, previous_digest: str, details: tuple[tuple[str, str], ...]) -> str:
        detail_text = "\x1e".join(f"{key}={value}" for key, value in details)
        payload = f"{sequence}\x1f{event}\x1f{principal_id}\x1f{timestamp:.9f}\x1f{previous_digest}\x1f{detail_text}"
        return sha256(payload.encode("utf-8")).hexdigest()

    def record(self, event: str, principal_id: str, timestamp: float | None = None, **details: Any) -> AuditEvent:
        if not isinstance(event, str) or not event.strip() or not isinstance(principal_id, str) or not principal_id.strip(): raise ValueError("audit identity required")
        stamp = time() if timestamp is None else timestamp
        if not isinstance(stamp, (int, float)) or isinstance(stamp, bool): raise TypeError("timestamp must be numeric")
        normalized = self._normalize_details(details)
        sequence = len(self._events)
        digest = self._digest(sequence, event, principal_id, float(stamp), self._head, normalized)
        entry = AuditEvent(sequence, event, principal_id, float(stamp), self._head, digest, normalized)
        self._events.append(entry); self._head = digest
        return entry

    def verify(self) -> bool:
        previous = "0" * 64
        for index, entry in enumerate(self._events):
            if entry.sequence != index or entry.previous_digest != previous: return False
            expected = self._digest(entry.sequence, entry.event, entry.principal_id, entry.timestamp, entry.previous_digest, entry.details)
            if entry.digest != expected: return False
            previous = entry.digest
        return previous == self._head
