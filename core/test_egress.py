import unittest

from .egress import EgressPolicy, EgressRequest

class EgressTests(unittest.TestCase):
    def test_default_deny_and_explicit_allow(self):
        policy = EgressPolicy()
        request = EgressRequest("agent", "Example.COM.", 443)
        self.assertFalse(policy.authorize(request))
        policy.allow("agent", "example.com", 443)
        self.assertTrue(policy.authorize(request))

    def test_protocol_and_port_are_bound(self):
        policy = EgressPolicy()
        policy.allow("agent", "example.com", 443, "tcp")
        self.assertTrue(policy.authorize(EgressRequest("agent", "example.com", 443, "tcp")))
        self.assertFalse(policy.authorize(EgressRequest("agent", "example.com", 443, "udp")))
        self.assertFalse(policy.authorize(EgressRequest("agent", "example.com", 80, "tcp")))

    def test_ip_addresses_are_canonicalized(self):
        policy = EgressPolicy()
        policy.allow("agent", "2001:0db8:0:0:0:0:0:1", 443)
        self.assertTrue(policy.authorize(EgressRequest("agent", "2001:db8::1", 443)))

    def test_capacity_is_bounded(self):
        policy = EgressPolicy(max_rules=1)
        policy.allow("agent", "example.com", 443)
        with self.assertRaises(OverflowError):
            policy.allow("agent", "example.net", 443)

    def test_revocation_is_immediate(self):
        policy = EgressPolicy()
        policy.allow("agent", "example.com", 443)
        policy.revoke("agent", "example.com", 443)
        self.assertFalse(policy.authorize(EgressRequest("agent", "example.com", 443)))

if __name__ == "__main__":
    unittest.main()
