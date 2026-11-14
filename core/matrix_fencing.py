"""Reference fencing primitive for a single protected resource.

A real deployment must persist this state atomically at the resource and obtain
monotonic epochs from a durable consensus-backed authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from threading import RLock


@dataclass(frozen=True)
class AppliedOperation:
    operation_id: str
    fencing_token: int
    payload_digest: str
    version: int


class FencedResource:
    def __init__(self) -> None:
        self._lock = RLock()
        self._highest_token = 0
        self._version = 0
        self._operations: dict[str, AppliedOperation] = {}

    @property
    def highest_token(self) -> int:
        with self._lock:
            return self._highest_token

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def activate(self, token: int) -> int:
        """Install a new epoch at the resource before the new holder acts."""
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            raise ValueError("fencing_token_must_be_positive_integer")
        with self._lock:
            if token <= self._highest_token:
                raise PermissionError("fencing_token_not_monotonic")
            self._highest_token = token
            return self._highest_token

    def apply(self, token: int, operation_id: str, payload: bytes) -> AppliedOperation:
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            raise ValueError("fencing_token_must_be_positive_integer")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id_required")
        if not isinstance(payload, bytes):
            raise TypeError("payload_must_be_bytes")
        digest = hashlib.sha256(payload).hexdigest()
        with self._lock:
            previous = self._operations.get(operation_id)
            if previous is not None:
                if previous.payload_digest != digest:
                    raise PermissionError("idempotency_key_payload_conflict")
                return previous
            if token != self._highest_token:
                raise PermissionError("stale_or_unactivated_fencing_token")
            self._version += 1
            result = AppliedOperation(operation_id, token, digest, self._version)
            self._operations[operation_id] = result
            return result
