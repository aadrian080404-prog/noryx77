from dataclasses import replace

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.actions import ActionGate, AuthorizationAuthority
from core.audit import AuditLog
from core.contracts import ActionSpec
from core.federation_admission import FederatedAdmissionBoundary
from core.federation_envelope import SignedExecutionEnvelope
from core.federated_action_audit import FederatedActionAuditRecorder
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


class _AdmissionRegistry:
    def is_registered(self, identity_id):
        return True


class _AdmissionVerifier:
    def verify_and_consume(self, envelope):
        return envelope


def _make_admission(policy_version="local-v1"):
    envelope = SignedExecutionEnvelope(
        schema_version=1, execution_id="exec-1", principal_id="tenant-1",
        agent_id="agent-1", task_type="search", capabilities=("search",),
        policy_version=policy_version, state_version="state-v1",
        issued_at=100, expires_at=160, nonce=b"n" * 32,
        issuer_key_id="issuer-1", signature=b"s" * 64,
    )
    boundary = FederatedAdmissionBoundary(
        _AdmissionVerifier(), principal_registry=_AdmissionRegistry(),
        agent_registry=_AdmissionRegistry(),
    )
    return boundary.admit(envelope)


def _setup(tmp_path, audit_log=None):
    agent_identity, _ = AgentIdentityAuthority.generate("agent-1")
    agents = SQLiteIdentityRegistry(tmp_path / "agents.sqlite")
    agents.register(agent_identity)
    agent_authority = AuthorizationAuthority(b"a" * 32, identity_registry=agents)

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
        policy, security, RuntimeLimits(), authorization=agent_authority,
    )
    audit_log = audit_log or AuditLog()
    recorder = FederatedActionAuditRecorder(audit_log, clock=lambda: 123.0)
    federated_gate = FederatedActionGate(
        gate, principal_authority, local_policy_version="local-v1",
        audit_recorder=recorder,
    )
    action = ActionSpec(
        action_id="search-1", action_type="search", target="local-index",
        parameters={"query": "bounded"}, risk_class="sensitive",
        requires_authorization=True, execution_id="exec-1",
    )
    admission = _make_admission("local-v1")
    agent_grant = agent_authority.issue(action, "exec-1", principal=agent_identity)
    principal_grant = principal_authority.issue(action, "exec-1", "tenant-1")
    return (
        federated_gate, agents, principals, agent_identity, action, admission,
        agent_grant, principal_grant, audit_log,
    )


def _dispatch(gate, agent, action, admission, agent_grant, principal_grant, executor):
    return gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search",
        executor=executor,
    )


def test_federated_action_requires_both_grants_local_policy_and_audit(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, log = _setup(tmp_path)
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("queued") or "queued",
    )
    assert decision.allowed is True
    assert result == "queued"
    assert dispatched == ["queued"]
    events = log.snapshot()
    assert len(events) == 2
    assert events[0]["event"] == "federated_action_decision"
    assert events[1]["event"] == "federated_action_outcome"
    assert events[1]["outcome"] == "dispatched"
    assert events[0]["principal_id"] == events[1]["principal_id"] == "tenant-1"
    assert events[0]["action_fingerprint"] == events[1]["action_fingerprint"]
    assert log.verify_integrity()


def test_federated_action_audit_failure_fails_closed_before_grant_consumption(tmp_path):
    class BrokenAudit:
        def record(self, *args, **kwargs):
            raise OSError("sink unavailable")

    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(
        tmp_path, audit_log=BrokenAudit()
    )
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert decision.reason == "federated_audit_unavailable"
    assert result is None
    assert dispatched == []


def test_federated_action_rejects_capability_claim_mismatch(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    dispatched = []
    decision, result = gate.authorize_and_dispatch(
        admission, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="payments",
        executor=lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False and result is None and dispatched == []


def test_federated_action_rejects_revoked_agent_before_dispatch(tmp_path):
    gate, agents, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    agents.revoke(agent.agent_id)
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False and result is None and dispatched == []


def test_federated_action_rejects_revoked_principal_before_dispatch(tmp_path):
    gate, _, principals, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    principals.revoke("tenant-1")
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False and result is None and dispatched == []


def test_federated_action_rejects_replay_of_either_grant(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    dispatched = []
    first, _ = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("first"),
    )
    second, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("replay"),
    )
    assert first.allowed is True and second.allowed is False
    assert result is None and dispatched == ["first"]


def test_federated_action_rejects_stale_policy_version(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    stale = _make_admission("local-v2")
    decision, result = gate.authorize_and_dispatch(
        stale, action, agent_identity=agent, agent_grant=agent_grant,
        principal_grant=principal_grant, required_capability="search",
        executor=lambda: None,
    )
    assert decision.allowed is False
    assert decision.reason == "federated_policy_version_mismatch"
    assert result is None


def test_federated_action_rejects_caller_fabricated_or_modified_admission(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(tmp_path)
    fabricated = replace(admission, policy_version="local-v1", _proof=b"")
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, fabricated, agent_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert decision.reason == "unverified_or_modified_federated_admission"
    assert result is None and dispatched == []



def test_federated_action_records_executor_failure_outcome(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, log = _setup(tmp_path)

    def broken_executor():
        raise OSError("private executor detail must not enter audit")

    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        broken_executor,
    )
    assert decision.allowed is False
    assert decision.reason == "federated_dispatch_failed"
    assert result is None
    events = log.snapshot()
    assert events[-1]["event"] == "federated_action_outcome"
    assert events[-1]["outcome"] == "executor_failed"
    assert "private executor detail" not in str(events)


def test_federated_action_records_agent_grant_rejection(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, log = _setup(tmp_path)
    dispatched = []
    from dataclasses import replace
    invalid_grant = replace(agent_grant, signature=b"x" * len(agent_grant.signature))
    decision, result = _dispatch(
        gate, agent, action, admission, invalid_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert result is None and dispatched == []
    assert log.snapshot()[-1]["outcome"] == "agent_grant_rejected"


def test_federated_action_surfaces_missing_final_audit_after_dispatch(tmp_path):
    class FailSecondRecord:
        def __init__(self):
            self.log = AuditLog()
            self.calls = 0

        def record(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise OSError("final audit unavailable")
            return self.log.record(*args, **kwargs)

    sink = FailSecondRecord()
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(
        tmp_path, audit_log=sink
    )
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("queued") or "queued",
    )
    assert dispatched == ["queued"]
    assert decision.allowed is False
    assert decision.reason == "federated_outcome_audit_unavailable_after_dispatch"
    assert result is None


def test_federated_gate_can_use_restart_durable_sqlite_audit_sink(tmp_path):
    from core.sqlite_federated_audit import SQLiteFederatedAuditLog

    path = tmp_path / "runtime-audit.sqlite"
    sink = SQLiteFederatedAuditLog(path, clock=lambda: 456.0)
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(
        tmp_path, audit_log=sink
    )
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: "locally-queued",
    )
    assert decision.allowed is True
    assert result == "locally-queued"
    assert len(sink.snapshot()) == 2
    sink.close()

    restarted = SQLiteFederatedAuditLog(path, clock=lambda: 457.0)
    events = restarted.snapshot()
    assert [event["event"] for event in events] == [
        "federated_action_decision", "federated_action_outcome"
    ]
    assert events[-1]["outcome"] == "dispatched"
    assert restarted.verify_integrity()
    restarted.close()



def test_federated_action_gate_anchors_decision_and_outcome_before_return(tmp_path):
    from core.federated_audit_anchor import (
        AnchoredFederatedAuditSink,
        FederatedAuditSynchronizer,
    )
    from core.sqlite_federated_audit import SQLiteFederatedAuditLog

    class FakeExternalAnchor:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        def read_checkpoint(self, namespace):
            return self.checkpoint

        def compare_and_advance(self, namespace, expected, next_checkpoint):
            if self.checkpoint != expected:
                return False
            self.checkpoint = next_checkpoint
            return True

    path = tmp_path / "gate-external-anchored.sqlite"
    durable_log = SQLiteFederatedAuditLog(path, clock=lambda: 987.0)
    external = FakeExternalAnchor(durable_log.checkpoint())
    synchronizer = FederatedAuditSynchronizer(
        durable_log, external, namespace="noryx7/runtime-gate"
    )
    anchored_sink = AnchoredFederatedAuditSink(durable_log, synchronizer)
    gate, _, _, agent, action, admission, agent_grant, principal_grant, _ = _setup(
        tmp_path, audit_log=anchored_sink
    )

    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: "locally-queued",
    )
    assert decision.allowed is True
    assert result == "locally-queued"
    assert [event["event"] for event in durable_log.snapshot()] == [
        "federated_action_decision", "federated_action_outcome"
    ]
    assert durable_log.checkpoint() == external.checkpoint
    assert external.checkpoint.sequence == 2
    durable_log.close()
