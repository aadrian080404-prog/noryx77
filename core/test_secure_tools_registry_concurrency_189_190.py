import threading

import pytest

from .crypto import CryptoIntegrity
from .secure_tools import SecureCapabilityRegistry


def test_189_concurrent_duplicate_registration_has_single_winner():
    registry = SecureCapabilityRegistry(CryptoIntegrity())
    barrier = threading.Barrier(8)
    successes = []
    failures = []

    def register(index):
        barrier.wait()
        try:
            registry.register("same", lambda target, params, i=index: i)
            successes.append(index)
        except ValueError as exc:
            failures.append(str(exc))

    threads = [threading.Thread(target=register, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(successes) == 1
    assert failures == ["duplicate_capability"] * 7
    assert registry.names() == ("same",)


def test_190_concurrent_resolution_never_observes_partial_capability_state():
    registry = SecureCapabilityRegistry(CryptoIntegrity())
    registry.register("safe", lambda target, params: "ok")
    barrier = threading.Barrier(16)
    errors = []
    resolved = []

    def resolve():
        try:
            barrier.wait()
            for _ in range(100):
                handler = registry.resolve("safe", risk_class="normal")
                assert callable(handler)
                resolved.append(handler)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=resolve) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(resolved) == 1600
