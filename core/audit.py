from copy import deepcopy
import hashlib
import json
from typing import Any


class AuditLog:
    """Append-only runtime evidence with tamper-evident hash chaining."""

    _GENESIS = "0" * 64

    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._digests: list[str] = []

    @classmethod
    def _canonicalize(cls, entry: dict[str, Any], previous_digest: str) -> bytes:
        payload = {
            "previous_digest": previous_digest,
            "entry": entry,
        }
        try:
            return json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("audit data must be JSON serializable") from exc

    @classmethod
    def _digest(cls, entry: dict[str, Any], previous_digest: str) -> str:
        return hashlib.sha256(cls._canonicalize(entry, previous_digest)).hexdigest()

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        entry = {"event": event, **data}
        stored = deepcopy(entry)
        previous_digest = self._digests[-1] if self._digests else self._GENESIS
        digest = self._digest(stored, previous_digest)
        self._events.append(stored)
        self._digests.append(digest)
        return deepcopy(stored)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)

    def verify_integrity(self) -> bool:
        if len(self._events) != len(self._digests):
            return False
        previous_digest = self._GENESIS
        for entry, expected_digest in zip(self._events, self._digests):
            if not isinstance(entry, dict) or not isinstance(expected_digest, str):
                return False
            try:
                actual_digest = self._digest(entry, previous_digest)
            except (TypeError, ValueError):
                return False
            if actual_digest != expected_digest:
                return False
            previous_digest = expected_digest
        return True

    def digest(self) -> str:
        return self._digests[-1] if self._digests else self._GENESIS
