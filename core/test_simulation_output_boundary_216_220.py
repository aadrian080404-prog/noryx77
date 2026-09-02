from .contracts import VerificationResult
from .reasoning import InternalSimulator, SimulationResult


class _MaliciousSimulation(SimulationResult):
    def __getattribute__(self, name):
        if name == "feasible":
            return True
        if name == "reason":
            return "feasible"
        return super().__getattribute__(name)


class _FalseSimulation(SimulationResult):
    def __getattribute__(self, name):
        if name == "feasible":
            return False
        if name == "reason":
            return "attacker_rejected"
        return super().__getattribute__(name)


def test_attack_216_simulation_verifier_rejects_malicious_subclass_that_reports_feasible():
    simulator = InternalSimulator()
    result = _MaliciousSimulation("h1", False, "attacker_rejected")
    check = simulator.verify((result,))
    assert check == VerificationResult(False, "simulation", "invalid_simulation_type")


def test_attack_217_simulation_verifier_rejects_false_subclass_even_when_reason_is_consistent():
    simulator = InternalSimulator()
    result = _FalseSimulation("h1", True, "feasible")
    check = simulator.verify((result,))
    assert check == VerificationResult(False, "simulation", "invalid_simulation_type")


def test_attack_218_simulation_verifier_rejects_mixed_exact_and_subclass_evidence():
    simulator = InternalSimulator()
    results = (
        SimulationResult("h1", True, "feasible"),
        _MaliciousSimulation("h2", False, "attacker_rejected"),
    )
    check = simulator.verify(results)
    assert check == VerificationResult(False, "simulation", "invalid_simulation_type")


def test_attack_219_simulation_verifier_accepts_only_exact_valid_evidence():
    simulator = InternalSimulator()
    check = simulator.verify((SimulationResult("h1", True, "feasible"),))
    assert check == VerificationResult(True, "simulation", "simulation_ok")


def test_attack_220_simulation_verifier_fails_closed_for_exact_rejected_evidence():
    simulator = InternalSimulator()
    check = simulator.verify((SimulationResult("h1", False, "simulation_rejected"),))
    assert check == VerificationResult(False, "simulation", "simulation_rejected")
