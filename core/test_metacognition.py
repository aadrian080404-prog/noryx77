import unittest

from .contracts import AgentResult, TaskSpec, VerificationResult
from .metacognition import MetacognitionEngine
from .planning import Plan, PlanStep
from .reasoning import Hypothesis, SimulationResult


class MetacognitionTests(unittest.TestCase):
    def _pipeline(self):
        task = TaskSpec("t1", "research", "analyze", "data", risk_class="normal", execution_id="exec-1")
        plan = Plan("t1", (PlanStep("s1", "analyze", "compute", "normal"),))
        hypotheses = (Hypothesis("t1:h0", "t1", "analyze", ("s1",)),)
        simulations = (SimulationResult("t1:h0", True, "feasible"),)
        results = (AgentResult("agent-1", "s1", "completed", "ok", VerificationResult(True, "agent_result"), "exec-1"),)
        return task, plan, hypotheses, simulations, results

    def test_confidence_is_derived_not_constant(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        check, reflection = engine.reflect(*args, VerificationResult(True, "hypersynth_result"))
        self.assertTrue(check.valid)
        self.assertGreaterEqual(reflection.confidence, 0.0)
        self.assertLessEqual(reflection.confidence, 1.0)
        self.assertGreaterEqual(reflection.calibration_score, 0.0)
        self.assertLessEqual(reflection.calibration_score, 1.0)
        self.assertEqual(reflection.recommended_action, "accept")

    def test_runtime_anomaly_requires_correction_and_fails_closed(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        check, reflection = engine.reflect(*args, VerificationResult(True, "hypersynth_result"), telemetry={"resource_pressure": 0.95})
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "reflection_requires_correction")
        self.assertTrue(reflection.correction_required)
        self.assertEqual(reflection.recommended_action, "replan")
        self.assertIn("resource_pressure", reflection.anomalies)
        self.assertEqual(reflection.error_attribution, (("allocation", "resource_pressure"),))

    def test_multiple_anomalies_escalate(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        check, reflection = engine.reflect(
            *args,
            VerificationResult(True, "hypersynth_result"),
            telemetry={"resource_pressure": 0.95, "latency_ratio": 1.5},
        )
        self.assertFalse(check.valid)
        self.assertEqual(reflection.recommended_action, "escalate")
        self.assertEqual(reflection.learning_signal, "adapt")

    def test_prior_confidence_is_bounded_and_affects_calibration(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        _, baseline = engine.reflect(*args, VerificationResult(True, "hypersynth_result"))
        _, adjusted = engine.reflect(*args, VerificationResult(True, "hypersynth_result"), prior_confidence=0.2)
        self.assertNotEqual(baseline.confidence, adjusted.confidence)
        self.assertGreaterEqual(adjusted.confidence, 0.0)
        self.assertLessEqual(adjusted.confidence, 1.0)
        self.assertGreaterEqual(adjusted.calibration_score, 0.0)
        self.assertLessEqual(adjusted.calibration_score, 1.0)

    def test_invalid_prior_confidence_fails_closed(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        check, reflection = engine.reflect(*args, VerificationResult(True, "hypersynth_result"), prior_confidence=2.0)
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "invalid_prior_confidence")
        self.assertIsNone(reflection)

    def test_state_fingerprint_is_deterministic_and_changes_with_anomaly(self):
        engine = MetacognitionEngine()
        args = self._pipeline()
        _, first = engine.reflect(*args, VerificationResult(True, "hypersynth_result"))
        _, second = engine.reflect(*args, VerificationResult(True, "hypersynth_result"))
        _, changed = engine.reflect(*args, VerificationResult(True, "hypersynth_result"), telemetry={"latency_ratio": 2.0})
        self.assertEqual(first.state_fingerprint, second.state_fingerprint)
        self.assertNotEqual(first.state_fingerprint, changed.state_fingerprint)
        self.assertEqual(len(first.state_fingerprint), 64)


if __name__ == "__main__":
    unittest.main()
