"""Binds cryptographic key retrieval to durable lifecycle state."""
from __future__ import annotations

from core.crypto import KEY_SIZE, KeyProvider
from core.key_lifecycle import ExternalKeyBoundary, KeyLifecycle


class LifecycleBoundKeyProvider(KeyProvider):
    """Fetch versioned key material only while its durable lifecycle is ACTIVE.

    The external boundary owns key material. This adapter caches no key bytes
    and rechecks lifecycle state on every retrieval.
    """

    def __init__(self, external: ExternalKeyBoundary, lifecycle: KeyLifecycle) -> None:
        if not isinstance(external, ExternalKeyBoundary) or not callable(getattr(external, "get_key", None)):
            raise TypeError("external_key_boundary_required")
        if not isinstance(lifecycle, KeyLifecycle):
            raise TypeError("key_lifecycle_required")
        if not getattr(lifecycle, "durable", False):
            raise ValueError("durable_key_lifecycle_required")
        self._external = external
        self._lifecycle = lifecycle

    def get_key(self, key_id: str) -> bytes:
        if not getattr(self._lifecycle, "durable", False):
            raise RuntimeError("durable_key_lifecycle_unavailable")
        record = self._lifecycle.require_active(key_id)
        key = self._external.get_key(record.key_id, record.version)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("external_key_provider_must_return_256_bit_key")
        return bytes(key)
