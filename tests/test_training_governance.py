import pytest

from core.training_governance import (
    EvaluationReport,
    TrainingExample,
    TrainingGovernance,
    TrainingStage,
)


def _example(example_id="ex-1", consent=True):
    return TrainingExample(
        example_id=example_id,
        input_text="Explain bounded execution.",
        target_text="Execution must respect explicit limits.",
        source="user_feedback",
        consent=consent,
    )


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
    report = EvaluationReport(
        candidate_id="candidate-1",
        baseline_score=0.80,
        candidate_score=0.82,
        safety_score=0.995,
        regression_free=True,
    )
    assert TrainingGovernance.admit(report) is TrainingStage.PROMOTED


def test_candidate_is_rejected_when_regression_or_safety_gate_fails():
    report = EvaluationReport(
        candidate_id="candidate-2",
        baseline_score=0.80,
        candidate_score=0.90,
        safety_score=0.80,
        regression_free=False,
    )
    assert TrainingGovernance.admit(report) is TrainingStage.REJECTED
