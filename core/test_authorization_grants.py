import unittest

from .actions import ActionGate, AuthorizationAuthority
from .contracts import ActionSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine


class AuthorizationGrantTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.clock = lambda: self.now
        self.authority = AuthorizationAuthority(b"k" * 32, clock=self.clock)
        policy = PolicyEngine()
        security = SecurityBoundary(policy, VerificationEngine())
        self.gate = ActionGate(policy, security, RuntimeLimits(max_actions_per_task=4), self.authority)

    def _action(self, execution="exec-a", action_id="a", *, parameters=None, risk_class="normal"):
        return ActionSpec(
            action_id,
            "compute",
            target="local",
            parameters={} if parameters is None else parameters,
            risk_class=risk_class,
            requires_authorization=True,
            execution_id=execution,
        )

    def test_valid_grant_allows_exact_action_once(self):
        action = self._action()
        grant = self.authority.issue(action, "exec-a")
        first = self.gate.authorize(action, execution_id="exec-a", grant=grant)
        second = self.gate.authorize(action, execution_id="exec-a", grant=grant)
        self.assertTrue(first.allowed)
        self.assertFalse(second.allowed)
        self.assertEqual(second.verification.reason, "invalid_authorization_grant")

    def test_grant_cannot_cross_execution(self):
        action_a = self._action("exec-a")
        grant = self.authority.issue(action_a, "exec-a")
        action_b = self._action("exec-b")
        decision = self.gate.authorize(action_b, execution_id="exec-b", grant=grant)
        self.assertFalse(decision.allowed)

    def test_grant_cannot_cross_action_id(self):
        action = self._action(action_id="a")
        grant = self.authority.issue(action, "exec-a")
        altered = self._action(action_id="b")
        decision = self.gate.authorize(altered, execution_id="exec-a", grant=grant)
        self.assertFalse(decision.allowed)

    def test_grant_cannot_cross_action_target(self):
        action = self._action()
        grant = self.authority.issue(action, "exec-a")
        altered = ActionSpec("a", "compute", target="remote", requires_authorization=True, execution_id="exec-a")
        decision = self.gate.authorize(altered, execution_id="exec-a", grant=grant)
        self.assertFalse(decision.allowed)

    def test_grant_cannot_cross_parameters(self):
        action = self._action(parameters={"amount": 10, "target": "alice"})
        grant = self.authority.issue(action, "exec-a")
        altered = self._action(parameters={"amount": 1000, "target": "alice"})
        decision = self.gate.authorize(altered, execution_id="exec-a", grant=grant)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_authorization_grant")

    def test_grant_cannot_cross_risk_class(self):
        action = self._action(risk_class="normal")
        grant = self.authority.issue(action, "exec-a")
        altered = self._action(risk_class="sensitive")
        decision = self.gate.authorize(altered, execution_id="exec-a", grant=grant)
        self.assertFalse(decision.allowed)

    def test_noncanonical_action_parameters_cannot_receive_grant(self):
        action = self._action(parameters={"payload": object()})
        with self.assertRaises(ValueError):
            self.authority.issue(action, "exec-a")

    def test_valid_grant_allows_canonical_mapping_order(self):
        action = self._action(parameters={"b": 2, "a": 1})
        grant = self.authority.issue(action, "exec-a")
        equivalent = self._action(parameters={"a": 1, "b": 2})
        first = self.gate.authorize(equivalent, execution_id="exec-a", grant=grant)
        self.assertTrue(first.allowed)

    def test_expired_grant_is_denied(self):
        action = self._action()
        grant = self.authority.issue(action, "exec-a", ttl=1)
        self.now = 101.0
        decision = self.gate.authorize(action, execution_id="exec-a", grant=grant)
        self.assertFalse(decision.allowed)

    def test_tampered_signature_is_denied(self):
        action = self._action()
        grant = self.authority.issue(action, "exec-a")
        tampered = type(grant)(
            grant.action_id,
            grant.action_type,
            grant.target,
            grant.execution_id,
            grant.principal_id,
            grant.principal_key_fingerprint,
            grant.nonce,
            grant.expires_at,
            "00" * 32,
        )
        decision = self.gate.authorize(action, execution_id="exec-a", grant=tampered)
        self.assertFalse(decision.allowed)

    def test_missing_grant_is_denied_for_authorized_action(self):
        action = self._action()
        decision = self.gate.authorize(action, execution_id="exec-a")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "authorization_required")

    def test_short_secret_rejected(self):
        with self.assertRaises(ValueError):
            AuthorizationAuthority(b"short")


if __name__ == "__main__":
    unittest.main()
