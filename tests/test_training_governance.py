import pytest

from core.training_governance import EvaluationReport, TrainingExample, TrainingGovernance, TrainingStage
from core.system_fabric import CanonicalSystemFabric


def _example(example_id="ex-1", consent=True):
    return TrainingExample(example_id=example_id, input_text="Explain bounded execution.", target_text="Execution must respect explicit limits.", source="user_feedback", consent=consent)


def test_training_dataset_requires_explicit_consent():
    governance = TrainingGovernance()
    with pytest.raises(PermissionError, match="training_consent_required"):
        governance.curate("dataset-1", (_example(consent=False),))


def test_training_dataset_has_deterministic_digest():
    governance = TrainingGovernance()
    first = governance.curate("dataset-1", (_example(),))
    second = governance.curate("dataset-1", (_example(),))
    assert first.digest == second.digest


def test_candidate_is_promoted_only_with_gain_safety_and_no_regression():
    report = EvaluationReport(candidate_id="candidate-1", baseline_score=0.80, candidate_score=0.82, safety_score=0.995, regression_free=True)
    assert TrainingGovernance.admit(report) is TrainingStage.PROMOTED


def test_candidate_is_rejected_when_regression_or_safety_gate_fails():
    report = EvaluationReport(candidate_id="candidate-2", baseline_score=0.80, candidate_score=0.90, safety_score=0.80, regression_free=False)
    assert TrainingGovernance.admit(report) is TrainingStage.REJECTED


def test_training_candidate_is_bound_to_runtime_fabric_without_raw_metadata():
    fabric = CanonicalSystemFabric()
    report = EvaluationReport(candidate_id="candidate-fabric", baseline_score=0.80, candidate_score=0.82, safety_score=0.995, regression_free=True)
    stage = TrainingGovernance.admit(report)
    fabric.record_execution(
        execution_id=f"training:{report.candidate_id}",
        client_id="noryx7-training",
        phase=stage.value,
        metadata={"candidate_id": report.candidate_id, "candidate_score": report.candidate_score, "private_example": "DO NOT STORE"},
    )
    record = fabric.memory.snapshot()[0]
    assert b"DO NOT STORE" not in record.payload
    assert b"candidate_score" not in record.payload
    assert b"metadata_digest=" in record.payload
