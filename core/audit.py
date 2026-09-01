from copy import deepcopy
import hashlib
import hmac
import json
import secrets
from typing import Any


class AuditLog:
    """Append-only runtime evidence authenticated by a keyed hash chain."""

    _GENESIS = b"NORYX7:AUDIT:GENESIS:v1"
    _RESERVED = frozenset({"auth"})

    def __init__(self, key: bytes | None = None):
        if key is None:
            key = secrets.token_bytes(32)
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("audit key must contain at least 32 bytes")
        self._key = bytes(key)
        self._events: list[dict[str, Any]] = []
        self._chain = self._GENESIS

    @staticmethod
    def _canonical(entry: dict[str, Any]) -> bytes:
        return json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    def _mac(self, previous: bytes, entry: dict[str, Any]) -> str:
        return hmac.new(self._key, previous + self._canonical(entry), hashlib.sha256).hexdigest()

    def record(self, event: str, **data) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("audit event must be non-empty text")
        if any(key in self._RESERVED for key in data):
            raise ValueError("audit reserved field")
        entry = {"event": event, **deepcopy(data)}
        mac = self._mac(self._chain, entry)
        entry["auth"] = mac
        self._events.append(entry)
        self._chain = bytes.fromhex(mac)
        return deepcopy(entry)

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)

    def verify(self, events=None) -> bool:
        """Verify the complete authenticated chain; any malformed/tampered entry fails closed."""
        candidate = self._events if events is None else events
        if not isinstance(candidate, (list, tuple)):
            return False
        previous = self._GENESIS
        for event in candidate:
            if not isinstance(event, dict):
                return False
            auth = event.get("auth")
            if not isinstance(auth, str) or len(auth) != 64:
                return False
            body = {key: deepcopy(value) for key, value in event.items() if key != "auth"}
            expected = self._mac(previous, body)
            if not hmac.compare_digest(auth, expected):
                return False
            try:
                previous = bytes.fromhex(auth)
            except ValueError:
                return False
        return True
