"""Bounded single-use replay protection for privileged NORYX7 authorizations."""
from __future__ import annotations

import threading

MAX_TOKENS = 4096
TOKEN_SIZE = 32


class AuthorizationReplayGuard:
    """Consumes cryptographic authorization tokens exactly once, fail-closed."""

    def __init__(self, *, max_tokens: int = MAX_TOKENS) -> None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= MAX_TOKENS:
            raise ValueError("invalid_max_tokens")
        self._max_tokens = max_tokens
        self._consumed: set[bytes] = set()
        self._lock = threading.Lock()

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def consumed_count(self) -> int:
        with self._lock:
            return len(self._consumed)

    def consume(self, token: bytes) -> bool:
        """Atomically consume token; return False for malformed/replayed/full input."""
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            if token in self._consumed:
                return False
            if len(self._consumed) >= self._max_tokens:
                return False
            self._consumed.add(bytes(token))
            return True

    def contains(self, token: bytes) -> bool:
        if not isinstance(token, bytes) or len(token) != TOKEN_SIZE:
            return False
        with self._lock:
            return token in self._consumed
