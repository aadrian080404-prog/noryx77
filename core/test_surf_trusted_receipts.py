from __future__ import annotations

import pytest

from core.identity import AgentIdentityAuthority, IdentityRegistry
from .surf_contracts import EvidenceRecord, Experiment, SystemGraph, SystemNode
from .surf_engine import SURFEngine, surf_receipt_statement


def _graph():
    evidence = EvidenceRecord(
        evidence_id="ev-1",
        kind="configuration",
        source="authorized-read-only-snapshot",
        summary="Observed service configuration",
        confidence=0.95,
        state="observed",
        execution_id="exec-1",
        provenance="snapshot:abc123",
    )
    graph = SystemGraph(
        graph_id="graph-1",
        nodes=(SystemNode("node-1", "service", "Example service", ("ev-1",)),),
        evidence=(evidence,),
    )
    return graph, evidence


def _trusted_provider():
    identity, private_key = AgentIdentityAuthority.generate("surf-verifier-1")
    registry = IdentityRegistry()
    registry.register(identity)

    def provider(receipt_type, statement):
        return AgentIdentityAuthority.sign(identity, private_key, statement)

    return identity, registry, provider


def test_surf_counts_only_identity_signed_receipts_in_trusted_mode():
    graph, evidence = _graph()
    _, registry, provider = _trusted_provider()
    engine = SURFEngine(
        evidence_verifier=lambda *_: True,
        trusted_receipt_provider=provider,
        trusted_identity_registry=registry,
    )
    result = engine.assess(graph, evidence=(evidence,))
    assert result.graph_valid is True
    assert result.verified_evidence_count == 1
    assert result.verification_trust_level == "trusted_identity_signed_receipts"


def test_surf_trusted_mode_does_not_fall_back_to_boolean_callbacks():
    graph, evidence = _graph()
    _, registry, _ = _trusted_provider()
    engine = SURFEngine(
        evidence_verifier=lambda *_: True,
        trusted_receipt_provider=lambda *_: None,
        trusted_identity_registry=registry,
    )
    result = engine.assess(graph, evidence=(evidence,))
    assert result.verified_evidence_count == 0
    assert result.verification_trust_level == "trusted_identity_signed_receipts"


def test_surf_rejects_receipts_from_unregistered_verifier_identity():
    graph, evidence = _graph()
    identity, private_key = AgentIdentityAuthority.generate("untrusted-verifier")
    registry = IdentityRegistry()

    def provider(receipt_type, statement):
        return AgentIdentityAuthority.sign(identity, private_key, statement)

    engine = SURFEngine(
        trusted_receipt_provider=provider,
        trusted_identity_registry=registry,
    )
    result = engine.assess(graph, evidence=(evidence,))
    assert result.verified_evidence_count == 0


def test_surf_receipt_is_bound_to_type_subject_and_context():
    graph, evidence = _graph()
    identity, private_key = AgentIdentityAuthority.generate("surf-verifier-1")
    registry = IdentityRegistry()
    registry.register(identity)
    original_statement = surf_receipt_statement("evidence", evidence, graph)
    signed = AgentIdentityAuthority.sign(identity, private_key, original_statement)

    engine = SURFEngine(
        trusted_receipt_provider=lambda *_: signed,
        trusted_identity_registry=registry,
    )
    changed_graph = SystemGraph(
        graph_id="graph-changed",
        nodes=graph.nodes,
        evidence=graph.evidence,
    )
    result = engine.assess(changed_graph, evidence=(evidence,))
    assert result.verified_evidence_count == 0


def test_surf_experiment_requires_signed_authorization_and_sandbox_receipts():
    identity, private_key = AgentIdentityAuthority.generate("surf-verifier-1")
    registry = IdentityRegistry()
    registry.register(identity)

    def provider(receipt_type, statement):
        return AgentIdentityAuthority.sign(identity, private_key, statement)

    engine = SURFEngine(
        trusted_receipt_provider=provider,
        trusted_identity_registry=registry,
    )
    experiment = Experiment(
        experiment_id="exp-1",
        hypothesis_id="hyp-1",
        objective="Run isolated read-only validation",
        variables={"mode": "read_only"},
        authorized=True,
        sandboxed=True,
        authorization_receipt="auth-receipt-1",
        sandbox_receipt="sandbox-receipt-1",
    )
    assert engine.approve_experiment(experiment) is True


def test_surf_requires_receipt_provider_and_registry_as_a_pair():
    _, registry, _ = _trusted_provider()
    with pytest.raises(ValueError, match="required_together"):
        SURFEngine(trusted_identity_registry=registry)
