from core.adversarial import AdversarialEngine
from core.evaluation import EvaluationDimension, EvaluationMatrix, EvaluationResult
from core.evaluation_campaign import EvaluationCampaign


def test_campaign_manifest_is_deterministic_and_partitioned() -> None:
    a = EvaluationCampaign(seed=42, cases=100_000, holdout_cases=1_000)
    b = EvaluationCampaign(seed=42, cases=100_000, holdout_cases=1_000)
    assert a.manifest == b.manifest
    assert a.manifest.training_cases == 99_000
    assert any(a.is_holdout(i) for i in range(100)) or any(not a.is_holdout(i) for i in range(100))


def test_generated_case_is_deterministic_and_bounded() -> None:
    a = EvaluationCampaign(seed=7, cases=1_000, holdout_cases=10)
    first = a.scenario(123, difficulty=90)
    second = a.scenario(123, difficulty=90)
    assert first == second
    assert first.scenario_id.startswith("adv-")
    assert len(first.sequence) <= 7


def test_holdout_partition_is_seed_sensitive() -> None:
    a = EvaluationCampaign(seed=1, cases=10_000, holdout_cases=500)
    b = EvaluationCampaign(seed=2, cases=10_000, holdout_cases=500)
    assert any(a.is_holdout(i) != b.is_holdout(i) for i in range(200))


def test_campaign_approval_fails_closed_on_empty_or_partial_matrix() -> None:
    campaign = EvaluationCampaign(seed=3, cases=100, holdout_cases=10)
    matrix = EvaluationMatrix()
    assert not campaign.approve(matrix)
    campaign.record(matrix, dimension=EvaluationDimension.SECURITY, passed=True, score=1.0, evidence="verified")
    assert not campaign.approve(matrix)


def test_campaign_approval_requires_every_dimension_and_all_pass() -> None:
    campaign = EvaluationCampaign(seed=4, cases=100, holdout_cases=10)
    matrix = EvaluationMatrix()
    for dimension in EvaluationDimension:
        matrix.record(EvaluationResult(dimension, True, 1.0, "independent-evidence"))
    assert campaign.approve(matrix)
    matrix.record(EvaluationResult(EvaluationDimension.RECOVERY, False, 0.2, "failure"))
    assert not campaign.approve(matrix)


def test_campaign_uses_existing_adversarial_generator_contract() -> None:
    campaign = EvaluationCampaign(seed=11, cases=1_000, holdout_cases=10)
    direct = AdversarialEngine(seed=11, max_scenarios=1_000).scenario(50, difficulty=30)
    assert campaign.scenario(50, difficulty=30) == direct
