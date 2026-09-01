import unittest

from .agents import DeterministicAgent
from .contracts import TaskSpec, VerificationResult
from .hypersynth import Hypersynth
from .reasoning import InternalSimulator, SimulationResult
from .router import ResourceRouter
from .verification import VerificationEngine


class MaliciousSimulator:
    def simulate(self, task, hypotheses):
        return tuple(SimulationResult(h.hypothesis_id, False, "forged-feasible") for h in hypotheses)

    def verify(self, simulations):
        return VerificationResult(True, "simulation", "forged_ok")


class MalformedSimulator:
    def simulate(self, task, hypotheses):
        return (object(),)

    def verify(self, simulations):
        return VerificationResult(True, "simulation", "forged_ok")


class Attack11Tests(unittest.TestCase):
    def task(self):
        return TaskSpec("attack11", "research", "objective", "input")

    def kernel(self, simulator):
        verifier = VerificationEngine()
        router = ResourceRouter()
        router.register(DeterministicAgent(verifier))
        return Hypersynth(verifier, router, simulator=simulator)

    def test_malicious_simulator_cannot_turn_valid_hypotheses_into_infeasible_execution(self):
        result = self.kernel(MaliciousSimulator()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "simulation_feasibility_mismatch")

    def test_malicious_simulator_cannot_invent_malformed_simulation_objects(self):
        result = self.kernel(MalformedSimulator()).run(self.task())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["phase"], "simulation")
        self.assertEqual(result["verification"].reason, "simulation_hypothesis_id_mismatch")

    def test_valid_simulation_still_reaches_execution(self):
        result = self.kernel(InternalSimulator()).run(self.task())
        self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
