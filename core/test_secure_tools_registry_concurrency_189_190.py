import threading
import unittest

from .crypto import CryptoIntegrity
from .secure_tools import SecureCapabilityRegistry


class SecureToolRegistryConcurrency189To190Tests(unittest.TestCase):
    def test_189_concurrent_duplicate_registration_has_single_winner(self):
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

        self.assertEqual(len(successes), 1)
        self.assertEqual(failures, ["duplicate_capability"] * 7)
        self.assertEqual(registry.names(), ("same",))

    def test_190_concurrent_resolution_never_observes_partial_capability_state(self):
        registry = SecureCapabilityRegistry(CryptoIntegrity())
        registry.register("safe", lambda target, params: "ok")
        barrier = threading.Barrier(16)
        errors = []
        resolved = []
        result_lock = threading.Lock()

        def resolve():
            try:
                barrier.wait()
                for _ in range(100):
                    handler = registry.resolve("safe", risk_class="normal")
                    self.assertTrue(callable(handler))
                    with result_lock:
                        resolved.append(handler)
            except Exception as exc:
                with result_lock:
                    errors.append(exc)

        threads = [threading.Thread(target=resolve) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(resolved), 1600)


if __name__ == "__main__":
    unittest.main()
