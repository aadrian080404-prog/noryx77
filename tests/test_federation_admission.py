import pytest

from core.federation_admission import FederatedAdmissionBoundary
from core.federation_envelope import EnvelopeRejected, SignedExecutionEnvelope


def _envelope():
    return SignedExecutionEnvelope(
        schema_version=1,
        execution_id="exec-1",
        principal_id="principal-1",
        agent_id="agent-1",
        task_type="analysis",
        capabilities=("memory.read", "task.execute"),
        policy_version="policy-1",
        state_version="state-1",
        issued_at=100,
        expires_at=160,
        nonce=b"n" * 32,
        issuer_key_id="issuer-1",
        signature=b"s" * 64,
    )


class Registry:
    def __init__(self, registered=True, error=None):
        self.registered = registered
        self.error = error
        self.calls = []

    def is_registered(self, identity_id):
        self.calls.append(identity_id)
        if self.error:
            raise self.error
        return self.registered


class Verifier:
    def __init__(self):
        self.calls = []

    def verify_and_consume(self, envelope):
        self.calls.append(envelope)
        return envelope


def test_admission_checks_distinct_principal_and_agent_registries():
    principals, agents, verifier = Registry(), Registry(), Verifier()
    boundary = FederatedAdmissionBoundary(
        verifier, principal_registry=principals, agent_registry=agents
    )

    result = boundary.admit(_envelope())

    assert principals.calls == ["principal-1"]
    assert agents.calls == ["agent-1"]
    assert verifier.calls == [_envelope()]
    assert result.principal_id == "principal-1"
    assert result.agent_id == "agent-1"
    assert result.asserted_capabilities == ("memory.read", "task.execute")


@pytest.mark.parametrize(
    ("principals", "agents", "reason"),
    [
        (Registry(False), Registry(), "unregistered_principal"),
        (Registry(), Registry(False), "unregistered_agent"),
        (Registry(error=RuntimeError("db down")), Registry(), "principal_membership_check_unavailable"),
        (Registry(), Registry(error=RuntimeError("db down")), "agent_membership_check_unavailable"),
    ],
)
def test_unknown_or_unavailable_membership_fails_before_nonce_consumption(
    principals, agents, reason
):
    verifier = Verifier()
    boundary = FederatedAdmissionBoundary(
        verifier, principal_registry=principals, agent_registry=agents
    )

    with pytest.raises(EnvelopeRejected, match=reason):
        boundary.admit(_envelope())

    assert verifier.calls == []


def test_admission_rejects_non_envelope_input():
    boundary = FederatedAdmissionBoundary(
        Verifier(), principal_registry=Registry(), agent_registry=Registry()
    )
    with pytest.raises(EnvelopeRejected, match="invalid_execution_envelope"):
        boundary.admit({"principal_id": "caller-controlled"})
