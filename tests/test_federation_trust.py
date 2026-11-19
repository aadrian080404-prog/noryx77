import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.federation_admission import FederatedAdmissionBoundary
from core.federation_envelope import (
    EnvelopeRejected,
    SignedExecutionEnvelope,
    sign_execution_envelope,
)
from core.federation_trust import build_federated_admission_boundary


class Registry:
    def __init__(self, *, registered=True, revoked=False):
        self.registered = registered
        self.revoked = revoked

    def is_registered(self, identity_id):
        return self.registered

    def is_revoked(self, identity_id):
        return self.revoked


class ReplayStore:
    def __init__(self):
        self.seen = set()

    def consume(self, issuer_key_id, nonce, expires_at, *, now):
        token = (issuer_key_id, nonce)
        if token in self.seen:
            return False
        self.seen.add(token)
        return True


def _signed_envelope(private_key, nonce=b"n" * 32):
    unsigned = SignedExecutionEnvelope(
        schema_version=1,
        execution_id="exec-1",
        principal_id="principal-1",
        agent_id="agent-1",
        task_type="analysis",
        capabilities=("memory.read",),
        policy_version="policy-1",
        state_version="state-1",
        issued_at=100,
        expires_at=160,
        nonce=nonce,
        issuer_key_id="issuer-1",
    )
    return sign_execution_envelope(
        unsigned, issuer_key_id="issuer-1", signing_key=private_key
    )


def _build(principals, agents):
    issuer = Ed25519PrivateKey.generate()
    boundary = build_federated_admission_boundary(
        trusted_public_keys={"issuer-1": issuer.public_key()},
        replay_store=ReplayStore(),
        principal_registry=principals,
        agent_registry=agents,
        is_issuer_revoked=lambda issuer_id: False,
        clock=lambda: 120,
    )
    return issuer, boundary


def test_factory_binds_principal_and_agent_revocation_callbacks():
    principals, agents = Registry(), Registry()
    issuer, boundary = _build(principals, agents)

    result = boundary.admit(_signed_envelope(issuer))

    assert result.principal_id == "principal-1"
    assert result.agent_id == "agent-1"


@pytest.mark.parametrize(
    ("principals", "agents", "reason"),
    [
        (Registry(revoked=True), Registry(), "execution_principal_revoked"),
        (Registry(), Registry(revoked=True), "execution_agent_revoked"),
    ],
)
def test_factory_rejects_revoked_identity_from_bound_store(
    principals, agents, reason
):
    issuer, boundary = _build(principals, agents)

    with pytest.raises(EnvelopeRejected, match=reason):
        boundary.admit(_signed_envelope(issuer))


def test_factory_requires_revocation_capability_on_both_registries():
    class MembershipOnly:
        def is_registered(self, identity_id):
            return True

    issuer = Ed25519PrivateKey.generate()
    with pytest.raises(TypeError, match="principal_revocation_registry_required"):
        build_federated_admission_boundary(
            trusted_public_keys={"issuer-1": issuer.public_key()},
            replay_store=ReplayStore(),
            principal_registry=MembershipOnly(),
            agent_registry=Registry(),
            is_issuer_revoked=lambda issuer_id: False,
            clock=lambda: 120,
        )


def test_real_verifier_rejects_replayed_signed_envelope():
    issuer, boundary = _build(Registry(), Registry())
    envelope = _signed_envelope(issuer)

    boundary.admit(envelope)
    with pytest.raises(EnvelopeRejected, match="execution_envelope_replayed"):
        boundary.admit(envelope)
