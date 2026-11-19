from dataclasses import replace

import pytest

from core.actions import ActionDecision
from core.audit import AuditLog
from core.contracts import ActionSpec, VerificationResult
from core.federation_admission import FederatedAdmissionBoundary
from core.federation_envelope import SignedExecutionEnvelope
from core.federated_action_audit import FederatedActionAuditRecorder


class Registry:
    def is_registered(self, identity_id):
        return True


class Verifier:
    def verify_and_consume(self, envelope):
        return envelope


def admission():
    envelope = SignedExecutionEnvelope(
        schema_version=1, execution_id="exec-audit", principal_id="tenant-a",
        agent_id="agent-a", task_type="search", capabilities=("search",),
        policy_version="policy-a", state_version="state-a",
        issued_at=100, expires_at=160, nonce=b"x" * 32,
        issuer_key_id="issuer-a", signature=b"s" * 64,
    )
    boundary = FederatedAdmissionBoundary(
        Verifier(), principal_registry=Registry(), agent_registry=Registry()
    )
    return boundary.admit(envelope)


def action(parameters=None):
    return ActionSpec(
        action_id="action-a", action_type="search", target="local-index",
        parameters=parameters or {"query": "sensitive-user-input"},
        risk_class="sensitive", requires_authorization=True,
        execution_id="exec-audit",
    )


def decision(allowed=True, reason="allowed"):
    return ActionDecision(
        allowed, reason, VerificationResult(allowed, "test", reason)
    )


def test_federated_audit_records_attribution_without_raw_parameters():
    log = AuditLog()
    recorder = FederatedActionAuditRecorder(log, clock=lambda: 123.5)
    result = recorder.record_decision(admission(), action(), decision())

    assert result["principal_id"] == "tenant-a"
    assert result["agent_id"] == "agent-a"
    assert result["execution_id"] == "exec-audit"
    assert result["policy_version"] == "policy-a"
    assert result["allowed"] is True
    assert result["timestamp"] == 123.5
    assert len(result["action_fingerprint"]) == 64
    assert "sensitive-user-input" not in repr(log.snapshot())
    assert log.verify_integrity() is True


def test_federated_audit_fingerprint_changes_with_action_parameters():
    first = FederatedActionAuditRecorder._action_fingerprint(
        action({"query": "one"})
    )
    second = FederatedActionAuditRecorder._action_fingerprint(
        action({"query": "two"})
    )
    assert first != second


def test_federated_audit_rejects_fabricated_or_modified_admission():
    verified = admission()
    fabricated = replace(verified, policy_version="policy-b")
    recorder = FederatedActionAuditRecorder(AuditLog())
    with pytest.raises(ValueError, match="verified_federated_admission_required"):
        recorder.record_decision(fabricated, action(), decision())


def test_federated_audit_rejects_noncanonical_or_oversized_parameters():
    recorder = FederatedActionAuditRecorder(AuditLog())
    with pytest.raises(ValueError, match="action_parameters_not_canonicalizable"):
        recorder._action_fingerprint(action({"value": object()}))
    with pytest.raises(ValueError, match="action_fingerprint_payload_too_large"):
        recorder._action_fingerprint(action({"value": "x" * 70000}))


def test_federated_audit_rejects_invalid_clock():
    recorder = FederatedActionAuditRecorder(AuditLog(), clock=lambda: float("nan"))
    with pytest.raises(RuntimeError, match="audit_clock_invalid"):
        recorder.record_decision(admission(), action(), decision())
