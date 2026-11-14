import unittest

from .actions import ActionGate
from .contracts import ActionSpec, TaskSpec, VerificationResult, AgentResult
from .hypersynth_runtime import HypersynthRuntime
from .limits import RuntimeLimits
from .policy import PolicyEngine
from .security import SecurityBoundary
from .verification import VerificationEngine


class RejectingVerifier(VerificationEngine):
    def verify_output(self, output, *, stage="result"):
        return VerificationResult(False, stage, "forced_rejection")


def task(**changes):
    values = dict(task_id="adv", task_type="research", objective="objective", input="input", risk_class="normal")
    values.update(changes)
    return TaskSpec(**values)


class AdversarialBoundaryTests(unittest.TestCase):
    def test_non_task_is_rejected(self):
        result = HypersynthRuntime().run(object())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["verification"].reason, "invalid_task_spec")

    def test_empty_identity_is_rejected(self):
        result = HypersynthRuntime().run(task(task_id=""))
        self.assertEqual(result["status"], "rejected")

    def test_oversized_input_is_rejected(self):
        limits = RuntimeLimits(max_input_chars=8)
        result = HypersynthRuntime(limits=limits).run(task(input="0123456789"))
        self.assertEqual(result["verification"].reason, "input_limit_exceeded")

    def test_oversized_objective_is_rejected(self):
        limits = RuntimeLimits(max_input_chars=8)
        result = HypersynthRuntime(limits=limits).run(task(objective="0123456789"))
        self.assertEqual(result["verification"].reason, "objective_limit_exceeded")

    def test_unknown_action_is_denied(self):
        verifier = VerificationEngine()
        security = SecurityBoundary(PolicyEngine(), verifier)
        gate = ActionGate(PolicyEngine(), security, RuntimeLimits())
        decision = gate.authorize(ActionSpec("x", "unknown"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "policy")

    def test_high_risk_action_is_denied(self):
        verifier = VerificationEngine()
        policy = PolicyEngine()
        gate = ActionGate(policy, SecurityBoundary(policy, verifier), RuntimeLimits())
        decision = gate.authorize(ActionSpec("x", "financial", risk_class="high"))
        self.assertFalse(decision.allowed)

    def test_negative_budget_is_denied(self):
        verifier = VerificationEngine()
        policy = PolicyEngine()
        gate = ActionGate(policy, SecurityBoundary(policy, verifier), RuntimeLimits())
        decision = gate.authorize(ActionSpec("x", "observe"), calls_used=-1)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "invalid_call_count")

    def test_budget_boundary_is_denied(self):
        verifier = VerificationEngine()
        policy = PolicyEngine()
        limits = RuntimeLimits(max_actions_per_task=1)
        gate = ActionGate(policy, SecurityBoundary(policy, verifier), limits)
        decision = gate.authorize(ActionSpec("x", "observe"), calls_used=1)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.verification.reason, "budget")

    def test_verifier_failure_is_not_promoted_to_success(self):
        result = HypersynthRuntime(verifier=RejectingVerifier()).run(task())
        self.assertNotEqual(result["status"], "completed")

    def test_high_risk_task_may_be_planned_but_external_action_is_not_authorized(self):
        result = HypersynthRuntime().run(task(risk_class="high"))
        self.assertEqual(result["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
