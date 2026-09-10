from core.cognitive_divergence import BranchingCognitionEngine
from core.contracts import TaskSpec
from core.monetization import MonetizationEngine
from core.pattern_neural import PatternNeuralNetwork
from core.scientific_fabric import PDEProblem, ScientificFabric, SimulationResult


def task(text="Compare the system architecture with a Navier-Stokes numerical model and identify anomalies"):
    return TaskSpec("cognitive-1", "research", text, "equation data and system failure", {}, (), "normal", "exec-1")


def test_branching_cognition_uses_multiple_lenses_and_neural_patterns():
    assessment = BranchingCognitionEngine().explore(task())
    assert assessment.verification.valid
    assert len(assessment.branches) == 5
    assert assessment.source_diversity >= 4
    assert assessment.neural_patterns
    assert BranchingCognitionEngine().verify(assessment).valid


def test_neural_pattern_network_is_bounded_and_deterministic():
    network = PatternNeuralNetwork()
    first = network.recognize_text("compare system failure and equation data")
    second = network.recognize_text("compare system failure and equation data")
    assert first == second
    assert all(0.0 <= item.score <= 1.0 for item in first)


def test_navier_stokes_boundary_verifies_independent_numerical_checks():
    fabric = ScientificFabric()
    problem = PDEProblem("navier_stokes_incompressible", 2, 1.0, 0.01, ("no_slip",), ("zero_velocity",), 0.001, 32)
    result = SimulationResult("finite_difference", 1e-5, 2e-5, 1e-4, True, "field-digest")
    verified = fabric.verify_simulation(task("Solve a 2D Navier-Stokes numerical case"), result)
    assert verified.valid
    assert fabric.classify(task("Solve a 2D Navier-Stokes numerical case")) == "navier_stokes"
    assert problem.is_well_formed()


def test_monetization_never_mints_revenue_from_unverified_close_or_click():
    engine = MonetizationEngine()
    offer = engine.create_offer(destination="https://example.com/sponsored")
    assert engine.loading_placement_enabled(offer)
    assert engine.admit_provider_event(offer, event_type="qualified_click", provider_reference="x", amount_minor=10, currency="EUR", verified=False) is None
    event = engine.admit_provider_event(offer, event_type="impression", provider_reference="provider-1", amount_minor=1, currency="eur", verified=True)
    assert event is not None
    assert event.verified is True
