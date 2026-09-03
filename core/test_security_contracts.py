import threading
import unittest
from dataclasses import replace

from .actions import ActionGate, AuthorizationAuthority
from .contracts import ActionSpec, TaskSpec
from .identity import AgentIdentityAuthority, IdentityRegistry
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine


class SecurityContractTests(unittest.TestCase):
    def setUp(self):
        verifier = VerificationEngine()
        policy = PolicyEngine()
        security = SecurityBoundary(policy, verifier)
        self.gate = ActionGate(policy, security, RuntimeLimits(max_actions_per_task=2))

    def setUp_authorized_gate(self):
        authority = AuthorizationAuthority(b"x" * 32)
        verifier = VerificationEngine()
        policy = PolicyEngine()
        security = SecurityBoundary(policy, verifier)
        return ActionGate(policy, security, RuntimeLimits(max_actions_per_task=100), authority), authority

    def setUp_identity_authorized_gate(self):
        registry = IdentityRegistry()
        identity, _ = AgentIdentityAuthority.generate("agent-a")
        registry.register(identity)
        authority = AuthorizationAuthority(b"x" * 32, identity_registry=registry)
        verifier = VerificationEngine()
        policy = PolicyEngine()
        security = SecurityBoundary(policy, verifier)
        gate = ActionGate(policy, security, RuntimeLimits(max_actions_per_task=100), authority)
        return gate, authority, registry, identity

    def test_malformed_action_denied(self):
        decision = self.gate.authorize(object())
        self.assertFalse(decision.allowed)

    def test_unknown_action_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "unknown"))
        self.assertFalse(decision.allowed)

    def test_high_risk_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "publish", risk_class="normal"))
        self.assertFalse(decision.allowed)

    def test_high_risk_class_denied_by_security(self):
        decision = self.gate.authorize(ActionSpec("a", "compute", risk_class="high"))
        self.assertFalse(decision.allowed)

    def test_authorization_flag_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "compute", requires_authorization=True))
        self.assertFalse(decision.allowed)

    def test_valid_grant_allows_exact_action_once(self):
        gate, authority = self.setUp_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-a")
        grant = authority.issue(action, "exec-a")

        first = gate.authorize(action, execution_id="exec-a", grant=grant)
        second = gate.authorize(action, execution_id="exec-a", grant=grant)

        self.assertTrue(first.allowed)
        self.assertFalse(second.allowed)
        self.assertEqual(second.verification.reason, "invalid_authorization_grant")

    def test_valid_grant_does_not_override_high_risk_policy(self):
        gate, authority = self.setUp_authorized_gate()
        action = ActionSpec("a", "publish", target="remote", requires_authorization=True, execution_id="exec-a")
        grant = authority.issue(action, "exec-a")

        decision = gate.authorize(action, execution_id="exec-a", grant=grant)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy")
        self.assertTrue(authority.verify(action, "exec-a", grant), "policy denial must not burn the grant")

    def test_grant_replay_is_single_winner_under_concurrency(self):
        gate, authority = self.setUp_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-a")
        grant = authority.issue(action, "exec-a")
        results = []
        lock = threading.Lock()

        def attempt():
            decision = gate.authorize(action, execution_id="exec-a", grant=grant)
            with lock:
                results.append(decision.allowed)

        threads = [threading.Thread(target=attempt) for _ in range(64)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(results), 1)

    def test_identity_bound_grant_allows_exact_principal_once(self):
        gate, authority, registry, identity = self.setUp_identity_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=identity)

        decision = gate.authorize(action, execution_id="exec-id", grant=grant, principal=identity)
        self.assertTrue(decision.allowed)
        self.assertFalse(gate.authorize(action, execution_id="exec-id", grant=grant, principal=identity).allowed)

    def test_identity_bound_grant_rejects_different_principal(self):
        gate, authority, registry, identity_a = self.setUp_identity_authorized_gate()
        identity_b, _ = AgentIdentityAuthority.generate("agent-b")
        registry.register(identity_b)
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=identity_a)

        decision = gate.authorize(action, execution_id="exec-id", grant=grant, principal=identity_b)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_authorization_grant")

    def test_revoked_identity_cannot_consume_unexpired_grant(self):
        gate, authority, registry, identity = self.setUp_identity_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=identity)
        registry.revoke(identity.agent_id)

        decision = gate.authorize(action, execution_id="exec-id", grant=grant, principal=identity)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_authorization_grant")

    def test_key_replacement_same_agent_id_cannot_use_old_grant(self):
        gate, authority, registry, old_identity = self.setUp_identity_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=old_identity)
        registry.revoke(old_identity.agent_id)
        new_identity, _ = AgentIdentityAuthority.generate(old_identity.agent_id)
        registry.register(new_identity)

        decision = gate.authorize(action, execution_id="exec-id", grant=grant, principal=new_identity)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_authorization_grant")

    def test_tampered_principal_fingerprint_breaks_signature(self):
        gate, authority, registry, identity = self.setUp_identity_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=identity)
        tampered = replace(grant, principal_key_fingerprint="0" * 64)

        decision = gate.authorize(action, execution_id="exec-id", grant=tampered, principal=identity)
        self.assertFalse(decision.allowed)

    def test_revoked_identity_blocks_all_concurrent_consumers(self):
        gate, authority, registry, identity = self.setUp_identity_authorized_gate()
        action = ActionSpec("a", "compute", target="local", requires_authorization=True, execution_id="exec-id")
        grant = authority.issue(action, "exec-id", principal=identity)
        registry.revoke(identity.agent_id)
        results = []
        lock = threading.Lock()

        def attempt():
            decision = gate.authorize(action, execution_id="exec-id", grant=grant, principal=identity)
            with lock:
                results.append(decision.allowed)

        threads = [threading.Thread(target=attempt) for _ in range(64)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(results), 0)

    def test_identity_registry_rejects_concurrent_duplicate_registration(self):
        registry = IdentityRegistry()
        identity, _ = AgentIdentityAuthority.generate("agent-a")
        errors = []
        lock = threading.Lock()

        def register():
            try:
                registry.register(identity)
            except ValueError as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=register) for _ in range(32)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(registry.is_trusted(identity))
        self.assertEqual(len(errors), 31)

    def test_budget_boundary(self):
        action = ActionSpec("a", "compute")
        self.assertTrue(self.gate.authorize(action, calls_used=1).allowed)
        self.assertFalse(self.gate.authorize(action, calls_used=2).allowed)

    def test_negative_call_count_denied(self):
        decision = self.gate.authorize(ActionSpec("a", "compute"), calls_used=-1)
        self.assertFalse(decision.allowed)

    def test_bound_action_requires_matching_execution(self):
        action = ActionSpec("a", "compute", execution_id="exec-a")
        decision = self.gate.authorize(action, execution_id="exec-a")
        self.assertTrue(decision.allowed)

    def test_bound_action_rejects_execution_transplant(self):
        action = ActionSpec("a", "compute", execution_id="exec-a")
        decision = self.gate.authorize(action, execution_id="exec-b")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "execution_identity_mismatch")

    def test_bound_action_cannot_fall_back_to_unbound_authorization(self):
        action = ActionSpec("a", "compute", execution_id="exec-a")
        decision = self.gate.authorize(action)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "execution_identity_required")

    def test_invalid_expected_execution_is_denied(self):
        action = ActionSpec("a", "compute", execution_id="exec-a")
        decision = self.gate.authorize(action, execution_id=" ")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_execution_identity")

    def test_policy_exception_fails_closed(self):
        class ExplodingPolicy:
            def allows(self, action):
                raise RuntimeError("policy backend failure")

        gate = ActionGate(ExplodingPolicy(), object(), RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "compute"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy_evaluation_failure")

    def test_security_exception_fails_closed(self):
        class ExplodingSecurity:
            def allows(self, action):
                raise RuntimeError("security backend failure")

        gate = ActionGate(PolicyEngine(), ExplodingSecurity(), RuntimeLimits())
        decision = gate.authorize(ActionSpec("a", "compute"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "security_evaluation_failure")


class TaskContractTests(unittest.TestCase):
    def test_invalid_risk_is_rejected(self):
        task = TaskSpec("t", "research", "objective", "input", risk_class="unknown")
        self.assertFalse(VerificationEngine().verify_task(task).valid)

    def test_empty_required_fields_are_rejected(self):
        task = TaskSpec("", "research", "objective", "input")
        self.assertFalse(VerificationEngine().verify_task(task).valid)


if __name__ == "__main__":
    unittest.main()
