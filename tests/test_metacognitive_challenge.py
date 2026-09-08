import hashlib

import pytest

from core.metacognitive_challenge import (
    AdaptiveChallengeController,
    ChallengeDomain,
    ChallengeScore,
    ChallengeSpec,
    ChallengeTrace,
    ImprovementEvidence,
    IndependentChallengeVerifier,
    MetacognitiveChallengeEvaluator,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def spec():
    return ChallengeSpec("c1", ChallengeDomain.NOVEL, 0.7, digest("prompt"), digest("answer"), 3)


def trace(success=True, self_claim=True):
    return ChallengeTrace(0.8, 0.9 if success else 0.2, "verify-and-revise", 3, 2, 2, digest("answer"), self_claim, success)


def verifier_fn(challenge, challenge_trace):
    return challenge_trace.answer_digest == challenge.expected_answer_digest and challenge_trace.task_success


def verification(challenge=None, challenge_trace=None, verifier=verifier_fn):
    return IndependentChallengeVerifier(verifier).verify(challenge or spec(), challenge_trace or trace())


def evaluate(challenge=None, challenge_trace=None):
    challenge = challenge or spec()
    challenge_trace = challenge_trace or trace()
    return MetacognitiveChallengeEvaluator().evaluate(challenge, challenge_trace, verification(challenge, challenge_trace))


def test_challenge_scores_are_bounded_and_evidence_based():
    score = evaluate()
    assert isinstance(score, ChallengeScore)
    assert 0.0 <= score.calibration <= 1.0
    assert score.task_performance == 1.0
    assert score.generalization == 1.0


def test_adaptive_controller_increases_only_after_strong_result():
    score = evaluate()
    assert AdaptiveChallengeController().next_level(3, score) == 4


def test_failed_challenge_does_not_claim_improvement():
    score = evaluate(challenge_trace=trace(False))
    assert score.task_performance == 0.0
    assert AdaptiveChallengeController().next_level(3, score) == 2


def test_trace_self_assertion_cannot_create_independent_verification():
    challenge = spec()
    forged = trace(self_claim=True)
    verification_result = verification(challenge, forged, verifier=lambda _challenge, _trace: False)
    assert verification_result.answer_matches
    assert not verification_result.independent_verified
    assert evaluate(challenge, forged) is not None
    score = MetacognitiveChallengeEvaluator().evaluate(challenge, forged, verification_result)
    assert score.task_performance == 0.0


def test_improvement_requires_independent_verification_evidence():
    evaluator = MetacognitiveChallengeEvaluator()
    challenge = spec()
    baseline_trace = ChallengeTrace(0.6, 0.5, "baseline", 1, 0, 0, digest("answer"), True, True)
    baseline = evaluator.evaluate(challenge, baseline_trace, verification(challenge, baseline_trace))
    candidate_trace = trace()
    candidate = evaluator.evaluate(challenge, candidate_trace, verification(challenge, candidate_trace))
    evidence = ImprovementEvidence("c1", baseline, candidate, digest("independent-verifier"))
    verifier = lambda value: value.challenge_id == "c1"
    assert AdaptiveChallengeController.improvement_is_verified(evidence, verifier)
    assert not AdaptiveChallengeController.improvement_is_verified(evidence, lambda _: False)


def test_invalid_digest_and_confidence_fail_closed():
    with pytest.raises(ValueError):
        ChallengeSpec("c1", ChallengeDomain.LOGIC, 0.5, "bad", digest("a"))
    with pytest.raises(ValueError):
        ChallengeTrace(1.2, 0.5, "x", 1, 0, 0, digest("a"), True, True)


def test_wrong_answer_cannot_be_scored_as_success():
    challenge = spec()
    bad_trace = ChallengeTrace(0.8, 0.9, "verify", 3, 0, 0, digest("wrong"), True, True)
    score = evaluate(challenge, bad_trace)
    assert score.task_performance == 0.0
    assert score.generalization == 0.0
