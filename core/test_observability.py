import unittest

from .observability import EventKind, SecurityEventBus


class SecurityEventBusTests(unittest.TestCase):
    def test_valid_sha256_evidence_is_accepted(self):
        bus = SecurityEventBus(max_events=1)
        event = bus.publish(
            EventKind.INTEGRITY_VIOLATION,
            component="core",
            severity=100,
            evidence_digest="a" * 64,
        )
        self.assertEqual(event.evidence_digest, "a" * 64)

    def test_non_hex_evidence_is_rejected(self):
        bus = SecurityEventBus()
        with self.assertRaises(ValueError):
            bus.publish(
                EventKind.INTEGRITY_VIOLATION,
                component="core",
                severity=100,
                evidence_digest="g" * 64,
            )

    def test_uppercase_evidence_is_rejected(self):
        bus = SecurityEventBus()
        with self.assertRaises(ValueError):
            bus.publish(
                EventKind.INTEGRITY_VIOLATION,
                component="core",
                severity=100,
                evidence_digest="A" * 64,
            )

    def test_capacity_failure_does_not_append_event(self):
        bus = SecurityEventBus(max_events=1)
        bus.publish(
            EventKind.AUTH_FAILURE,
            component="core",
            severity=100,
            evidence_digest="b" * 64,
        )
        with self.assertRaises(RuntimeError):
            bus.publish(
                EventKind.AUTH_FAILURE,
                component="core",
                severity=100,
                evidence_digest="c" * 64,
            )
        self.assertEqual(len(bus.snapshot()), 1)


if __name__ == "__main__":
    unittest.main()
