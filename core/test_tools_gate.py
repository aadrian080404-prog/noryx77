import unittest

from .actions import ActionGate
from .contracts import ActionSpec
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .tools import ToolExecutor
from .verification import VerificationEngine


class ToolExecutorGateTests(unittest.TestCase):
    def setUp(self):
        self.verifier = VerificationEngine()
        self.policy = PolicyEngine()
        self.security = SecurityBoundary(self.policy, self.verifier)
        self.gate = ActionGate(self.policy, self.security, RuntimeLimits(max_actions_per_task=1))
        self.executor = ToolExecutor(self.gate, self.verifier)

    def test_constructor_requires_canonical_gate_or_policy(self):
        with self.assertRaises(ValueError):
            ToolExecutor(object(), self.verifier)

    def test_gate_denial_prevents_handler_execution(self):
        calls = []

        def handler(target, params):
            calls.append(target)
            return target

        self.executor.capabilities.register("publish", handler)
        action = ActionSpec("a1", "publish", target="blocked", risk_class="high")
        output, check = self.executor.execute(action)
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(calls, [])

    def test_gate_budget_prevents_handler_execution(self):
        calls = []
        self.executor.capabilities.register("search", lambda target, params: calls.append(target) or target)
        action = ActionSpec("a2", "search", target="blocked")
        output, check = self.executor.execute(action, calls_used=1)
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(calls, [])

    def test_allowed_execution_is_verified_after_gate(self):
        self.executor.capabilities.register("search", lambda target, params: target)
        output, check = self.executor.execute(ActionSpec("a3", "search", target="ok"))
        self.assertEqual(output, "ok")
        self.assertTrue(check.valid)
        self.assertEqual(check.stage, "tool_result")

    def test_authorized_tool_requires_execution_identity_grant_and_principal(self):
        calls = []
        self.executor.capabilities.register("publish", lambda target, params: calls.append(target) or target)
        action = ActionSpec(
            "a4",
            "publish",
            target="protected",
            execution_id="exec-4",
            requires_authorization=True,
        )
        output, check = self.executor.execute(action, execution_id="exec-4")
        self.assertIsNone(output)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "authorization_required")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()


def test_high_risk_external_provider_crosses_action_gate_runtime_and_signed_journal(monkeypatch):
    import json
    from core.actions import AuthorizationAuthority
    from core.identity import AgentIdentityAuthority
    from core.frontier_capabilities import ExternalProviderCapability
    from core.tools import ToolExecutor
    from noryx7_runtime.attestation import Ed25519AttestationSigner
    from noryx7_runtime.engine import RuntimeEngine
    from noryx7_runtime.state import StateJournal

    identity, private_key = AgentIdentityAuthority.generate("browser-agent")
    registry = __import__("core.identity", fromlist=["IdentityRegistry"]).IdentityRegistry()
    registry.register(identity)
    signer = Ed25519AttestationSigner(private_key)
    journal = StateJournal(require_signatures=True, verifier=signer, runtime_id="provider-e2e")
    engine = RuntimeEngine(
        attestation_signer=signer,
        runtime_id="provider-e2e",
        state_journal=journal,
    )
    authority = AuthorizationAuthority(b"provider-e2e-secret-" + b"x" * 16, identity_registry=registry)
    gate = ActionGate(self.policy, self.security, RuntimeLimits(max_actions_per_task=1), authorization=authority)
    executor = ToolExecutor(gate, self.verifier, runtime_engine=engine)

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _limit):
            return json.dumps({
                "protocol": "NORYX7_PROVIDER_V1",
                "provider": "flights",
                "status": "completed",
                "execution_id": "provider-e2e-exec",
                "idempotency_key": "provider-e2e-exec",
                "verified": True,
                "receipt": {"receipt_id": "receipt-e2e-1"},
                "effect": {"status": "applied"},
                "result": {"booking_id": "BOOK-E2E"},
            }).encode()

    monkeypatch.setenv("NORYX7_FLIGHTS_ENDPOINT", "https://provider.example.test/execute")
    monkeypatch.setenv("NORYX7_FLIGHTS_TOKEN", "provider-token")
    import core.frontier_capabilities as frontier
    monkeypatch.setattr(frontier, "urlopen", lambda *_args, **_kwargs: Response())

    action = ActionSpec(
        "provider-e2e-step",
        "flights",
        target="book",
        parameters={"operation": "book"},
        risk_class="high",
        requires_authorization=True,
        execution_id="provider-e2e-exec",
    )
    grant = authority.issue(action, "provider-e2e-exec", principal=identity)
    output, check = executor.execute(
        action,
        execution_id="provider-e2e-exec",
        grant=grant,
        principal=identity,
    )

    assert check.valid
    assert output["receipt"]["receipt_id"] == "receipt-e2e-1"
    assert output["effect"]["status"] == "applied"
    entries = journal.snapshot()
    assert len(entries) == 1
    assert entries[0].execution_id == "provider-e2e-exec"
    assert entries[0].step_id == "provider-e2e-step"
    assert entries[0].external_commit_status == "not_required"
    assert entries[0].output_digest
    assert engine.runtime_id == "provider-e2e"
    engine.close()
    journal.close()
