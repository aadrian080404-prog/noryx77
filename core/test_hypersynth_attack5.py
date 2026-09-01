import unittest

from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .reasoning import HypothesisEngine, InternalSimulator
from .router import ResourceRouter
from .agents import DeterministicAgent
from .verification import VerificationEngine


class DuplicateHypothesisEngine(HypothesisEngine):
    def generate(self, task, plan):
        base = super().generate(task, plan)
        return base + (base[0],)


class Attack5Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack5", "research", "objective", "input", risk_class="normal")

    def test_duplicate_hypothesis_identity_fails_closed(self):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        kernel = Hypersynth(verifier, router, hypothesis_engine=DuplicateHypothesisEngine())
        result = kernel.run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "hypothesis")

    def test_internal_simulator_rejects_empty_collection(self):
        check = InternalSimulator().verify(())
        self.assertFalse(check.valid)
        self.assertEqual(check.reason, "no_simulations")


if __name__ == "__main__":
    unittest.main()
