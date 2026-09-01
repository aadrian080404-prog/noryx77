from copy import deepcopy
from typing import Any


class AuditLog:
    """Append-only runtime evidence. It does not authorize or mutate execution."""

    def __init__(self):
        self._events: list[dict[str, Any]] = []

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        entry = {"event": event, **deepcopy(data)}
        self._events.append(entry)
        return deepcopy(entry)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)
