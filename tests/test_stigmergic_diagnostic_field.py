import hashlib

from core.stigmergic_diagnostic_field import (
    DiagnosticTrace,
    StigmergicDiagnosticField,
)


def make_trace(principal, agent, *, claim="claim-a", polarity=1,
               strength=1.0, evidence=None, now=1000.0, ttl=600.0):
    evidence = evidence or f"evidence-{principal}-{agent}-{polarity}"
    return DiagnosticTrace(
        claim_id=claim,
        principal_id=principal,
        agent_id=agent,
        evidence_id=evidence,
        evidence_fingerprint=hashlib.sha256(evidence.encode()).hexdigest(),
        polarity=polarity,
        strength=strength,
        issued_at=now,
        expires_at=now + ttl,
        signature="signed-envelope",
    )


def test_independent_principals_corroborate_but_agents_do_not_multiply_quorum():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 1000.0, minimum_principals=3
    )
    assert field.submit(make_trace("p1", "a1"))
    assert field.submit(make_trace("p1", "a2", evidence="second-p1"))
    assert field.submit(make_trace("p2", "a3"))
    result = field.evaluate("claim-a")
    assert result.status == "insufficient_evidence"
    assert result.active_traces == 2
    assert result.positive_principals == 2


def test_three_independent_positive_principals_corroborate():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 1000.0, minimum_principals=3
    )
    for principal in ("p1", "p2", "p3"):
        assert field.submit(make_trace(principal, "agent"))
    result = field.evaluate("claim-a")
    assert result.status == "corroborated"
    assert result.confidence == 1.0


def test_contradiction_is_visible_not_silently_outvoted():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 1000.0,
        minimum_principals=3, corroboration_threshold=0.7,
        rejection_threshold=0.7,
    )
    assert field.submit(make_trace("p1", "a1"))
    assert field.submit(make_trace("p2", "a2"))
    assert field.submit(make_trace("p3", "a3", polarity=-1))
    assert field.evaluate("claim-a").status == "contested"


def test_expired_traces_do_not_contribute():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 2000.0, minimum_principals=2
    )
    for principal in ("p1", "p2"):
        assert field.submit(make_trace(principal, "agent", now=1000.0, ttl=10.0))
    result = field.evaluate("claim-a")
    assert result.status == "insufficient_evidence"
    assert result.active_traces == 0


def test_decay_reduces_old_evidence_weight():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 1600.0,
        half_life_seconds=100.0, minimum_principals=2,
    )
    for principal in ("p1", "p2"):
        assert field.submit(make_trace(principal, "agent", now=1000.0, ttl=1000.0))
    result = field.evaluate("claim-a")
    assert 0 < result.positive_weight < 0.5


def test_rejects_duplicate_evidence_and_unverified_trace():
    field = StigmergicDiagnosticField(
        lambda trace: trace.signature == "valid",
        clock=lambda: 1000.0,
    )
    invalid = make_trace("p1", "a1")
    assert not field.submit(invalid)
    valid = DiagnosticTrace(**{**invalid.__dict__, "signature": "valid"})
    assert field.submit(valid)
    assert not field.submit(valid)


def test_rejects_excessive_ttl_and_invalid_polarity():
    field = StigmergicDiagnosticField(lambda trace: True, clock=lambda: 1000.0)
    assert not field.submit(make_trace("p1", "a1", ttl=field.MAX_TTL_SECONDS + 1))
    bad = make_trace("p2", "a2")
    bad = DiagnosticTrace(**{**bad.__dict__, "polarity": 0})
    assert not field.submit(bad)


def test_corroboration_is_not_an_authorization_decision():
    field = StigmergicDiagnosticField(
        lambda trace: True, clock=lambda: 1000.0, minimum_principals=2
    )
    for principal in ("p1", "p2"):
        assert field.submit(make_trace(principal, "agent"))
    result = field.evaluate("claim-a")
    assert result.status == "corroborated"
    assert not hasattr(result, "allowed")
    assert not hasattr(result, "execute")
