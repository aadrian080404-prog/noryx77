from copy import deepcopy
from typing import Any


class AuditLog:
    """Append-only runtime evidence isolated from caller-owned mutable data."""

    def __init__(self):
        self._events: list[dict[str, Any]] = []

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        entry = {"event": event, **data}
        stored = deepcopy(entry)
        self._events.append(stored)
        return deepcopy(stored)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)
