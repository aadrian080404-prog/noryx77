from dataclasses import asdict
from typing import Any

class AuditLog:
    """Append-only runtime evidence. It does not authorize or mutate execution."""
    def __init__(self):
        self._events: list[dict[str, Any]] = []

    def record(self, event: str, **data) -> dict[str, Any]:
        entry = {"event": event, **data}
        self._events.append(entry)
        return dict(entry)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)
