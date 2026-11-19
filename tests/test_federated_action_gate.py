from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.actions import ActionGate, AuthorizationAuthority
from core.contracts import ActionSpec
from core.federation_admission import FederatedAdmission
from core.federated_action_gate import FederatedActionGate
from core.identity import AgentIdentityAuthority
from core.limits import RuntimeLimits
from core.policy import PolicyEngine
from core.principal_authorization import PrincipalAuthorizationAuthority
from core.principal_identity import PrincipalIdentity
from core.security import SecurityBoundary
from core.sqlite_identity import SQLiteIdentityRegistry
from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry
from core.verification import VerificationEngine


def _setup(tmp_path):
    agent_identity, _ = AgentIdentityAuthority.generate("agent-1")
    agents = SQLiteIdentityRegistry(tmp_path / "agents.sqlite")
    agents.register(agent_identity)
    agent_authority = AuthorizationAuthority(
        b"a" * 32, identity_registry=agents
    )

    principal_key = Ed25519PrivateKey.generate()
    principal_public = principal_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    principal_identity = PrincipalIdentity("tenant-1", principal_public)
    principals = SQLitePrincipalIdentityRegistry(tmp_path / "principals.sqlite")
    principals.register(principal_identity)
    principal_authority = PrincipalAuthorizationAuthority(
        b"p" * 32, tmp_path / "principal-grants.sqlite", principals
    )

    policy = PolicyEngine()
    security = SecurityBoundary(policy, VerificationEngine())
    gate = ActionGate(
        policy, security, RuntimeLimits(),
        authorization=agent_authority,
    )
    federated_gate = FederatedActionGate(gate, principal_authority)
    action = ActionSpec(
        action_id="search-1", action_type="search", target="local-index",
        parameters={"query": "bounded"}, risk_class="sensitive",
        requires_authorization=True, execution_id="exec-1",
    )
    admission = FederatedAdmission(
        execution_id="exec-1", principal_id="tenant-1", agent_id="agent-1",
        task_type="search", asserted_capabilities=("search",),
        policy_version="local-v1", state_version="state-v1",
        issuer_key_id="issuer-1",
    )
    agent_grant = agent_authority.issue(
        action, "exec-1", principal=agent_identity
    )
    principal_grant = principal_authority.issue(
        action, "exec-1", "tenant-1"
    )
    return (
        federated_gate, agents, principals, agent_identity, action, admission,
        agent_grant, principal_grant,
    )


def test_federated_action_requires_both_grants_and_local_policy(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search", local_policy_version="local-v1",
        executor=lambda: dispatched.append("queued") or "queued",
    )
    assert decision.allowed is True
    assert result == "queued"
    assert dispatched == ["queued"]


def test_federated_action_rejects_capability_claim_mismatch(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="payments",
        executor=lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert result is None
    assert dispatched == []


def test_federated_action_rejects_revoked_agent_before_dispatch(tmp_path):
    gate, agents, _, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    agents.revoke(agent.agent_id)
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search", local_policy_version="local-v1",
        executor=lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert result is None
    assert dispatched == []


def test_federated_action_rejects_revoked_principal_before_dispatch(tmp_path):
    gate, _, principals, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    principals.revoke("tenant-1")
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search", local_policy_version="local-v1",
        executor=lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert result is None
    assert dispatched == []


def test_federated_action_rejects_replay_of_either_grant(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    dispatched = []
    first, _ = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search", local_policy_version="local-v1",
        executor=lambda: dispatched.append("first"),
    )
    second, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search", local_policy_version="local-v1",
        executor=lambda: dispatched.append("replay"),
    )
    assert first.allowed is True
    assert second.allowed is False
    assert result is None
    assert dispatched == ["first"]



def test_federated_action_rejects_stale_policy_version(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant = _setup(tmp_path)
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search",
        local_policy_version="local-v2",
        executor=lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert result is None
    assert dispatched == []
