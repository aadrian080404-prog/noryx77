from core.contracts import TaskSpec
from core.universal_intelligence import DomainAssessment, Evidence, UniversalIntelligenceFabric


def task():
    return TaskSpec(
        task_id="uif-task",
        task_type="research",
        objective="evaluate a bounded question",
        input="question",
        constraints={},
        verification_requirements=("universal_intelligence",),
        risk_class="normal",
        execution_id="uif-exec",
    )


def evidence():
    return (Evidence("e1", "source-a", "supported claim", 0.9),)


def test_fabric_accepts_verified_low_uncertainty_assessment():
    result = UniversalIntelligenceFabric().assess(
        task(),
        (DomainAssessment("scientific", "bounded conclusion", evidence(), 0.9, 0.1, (), "normal", "pythagorean"),),
        budget="specialist",
    )
    assert result.verification.valid
    assert result.commit_eligible
    assert result.evidence_coverage == 0.9


def test_fabric_blocks_contradiction_from_trusted_commit():
    result = UniversalIntelligenceFabric().assess(
        task(),
        (DomainAssessment("legal", "contested conclusion", evidence(), 0.8, 0.2, ("source conflict",), "normal", "apollonian"),),
    )
    assert not result.verification.valid
    assert result.contradiction
    assert not result.commit_eligible


def test_fabric_blocks_high_uncertainty():
    result = UniversalIntelligenceFabric().assess(
        task(),
        (DomainAssessment("finance", "scenario", evidence(), 0.4, 0.8, (), "normal", "eurelian"),),
    )
    assert not result.verification.valid
    assert not result.commit_eligible


def test_fabric_rejects_malformed_assessment_and_invalid_budget():
    fabric = UniversalIntelligenceFabric()
    malformed = fabric.assess(task(), (object(),))
    assert not malformed.verification.valid
    assert malformed.verification.reason == "malformed_domain_assessment"

    invalid_budget = fabric.assess(task(), (DomainAssessment("science", "ok", evidence(), 0.8, 0.1),), budget="unbounded")
    assert not invalid_budget.verification.valid
    assert invalid_budget.verification.reason == "invalid_cognitive_budget"


def test_specialists_have_no_authorization_or_commit_surface():
    assert not hasattr(DomainAssessment, "authorize")
    assert not hasattr(DomainAssessment, "commit")
    assert not hasattr(UniversalIntelligenceFabric, "authorize")
