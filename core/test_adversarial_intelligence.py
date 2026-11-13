import pytest

from .adversarial_intelligence import (
    AdversarialTwin, AnchoredBipolicy, DefensiveProposal, Evidence,
    IndependentJury, MetaMorphSES, SelfPlaySimulator, VerifiedOutcome, Verdict,
)


def ev(name, source):
    return Evidence(name, source, "a" * 64, True, True)


def test_independent_jury_accepts_only_reversible_low_impact_proposal():
    jury = IndependentJury()
    proposal = DefensiveProposal("p1", "isolate_test_fixture", "sandbox-1", True, False)
    assert jury.adjudicate(proposal, (ev("e1", "sensor-a"), ev("e2", "sensor-b"))).verdict is Verdict.ACCEPT


def test_jury_disagreement_is_inconclusive_not_majority_authority():
    jury = IndependentJury()
    proposal = DefensiveProposal("p1", "rotate_global_keys", "all-tenants", True, True)
    result = jury.adjudicate(proposal, (ev("e1", "sensor-a"), ev("e2", "sensor-b")))
    assert result.verdict is Verdict.INCONCLUSIVE


def test_jury_rejects_single_or_unverified_evidence():
    jury = IndependentJury()
    proposal = DefensiveProposal("p1", "isolate", "sandbox", True, False)
    assert jury.adjudicate(proposal, (ev("e1", "sensor-a"),)).verdict is Verdict.INCONCLUSIVE
    bad = Evidence("e2", "sensor-b", "b" * 64, False, True)
    assert jury.adjudicate(proposal, (ev("e1", "sensor-a"), bad)).verdict is Verdict.INCONCLUSIVE


def test_anchor_policy_reference_is_immutable_while_candidate_changes():
    policies = AnchoredBipolicy({"deny_unknown": "true"}, {"threshold": "3"})
    original = policies.reference_digest
    policies.update_candidate({"threshold": "4"})
    assert policies.reference_digest == original
    assert policies.reference_intact()
    assert policies.candidate_version == 2


def test_meta_learning_requires_verified_outcomes_and_is_bounded():
    meta = MetaMorphSES(threshold=3, minimum=1, maximum=4)
    with pytest.raises(PermissionError):
        meta.learn(VerifiedOutcome("s", "p", True, ()))
    for index in range(5):
        value = meta.learn(VerifiedOutcome(f"s{index}", "p", False, (ev(f"e{index}", "independent"),)))
    assert value == 4
    assert meta.failures == 5


def test_adversarial_twin_learns_from_defense_outcome():
    twin = AdversarialTwin(seed=7, max_rounds=2)
    before = twin.meta.threshold
    twin.learn(VerifiedOutcome("scenario", "defense", True, (ev("a", "sensor-a"),)))
    assert twin.meta.threshold == before - 1
    assert len(twin.scenario_id(0)) == 24


def test_self_play_is_bounded_and_has_no_execution_adapter():
    sim = SelfPlaySimulator(max_rounds=2)
    assert sim.run(("replay", "tamper"), ("reject", "quarantine")) == (
        ("replay", "reject"), ("tamper", "quarantine")
    )
    with pytest.raises(ValueError):
        sim.run(("one",), ())
