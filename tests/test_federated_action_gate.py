import pytest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event

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
from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry
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
    binding_registry = SQLitePrincipalAgentBindingRegistry(
        tmp_path / "principal-agent-bindings.sqlite",
        principal_registry=principals,
        agent_registry=agents,
    )
    binding_registry.bind("tenant-1", "agent-1")

    policy = PolicyEngine()
    security = SecurityBoundary(policy, VerificationEngine())
    gate = ActionGate(
        policy, security, RuntimeLimits(), authorization=agent_authority,
    )
    audit_log = audit_log or AuditLog()
    recorder = FederatedActionAuditRecorder(audit_log, clock=lambda: 123.0)
    federated_gate = FederatedActionGate(
        gate, principal_authority, binding_registry,
        local_policy_version="local-v1", audit_recorder=recorder,
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


def test_federated_action_rechecks_live_principal_agent_binding_at_dispatch(tmp_path):
    gate, _, _, agent, action, admission, agent_grant, principal_grant, log = _setup(tmp_path)
    gate._bindings.revoke_binding("tenant-1", agent.agent_id)
    dispatched = []
    decision, result = _dispatch(
        gate, agent, action, admission, agent_grant, principal_grant,
        lambda: dispatched.append("unsafe"),
    )
    assert decision.allowed is False
    assert decision.reason == "principal_agent_binding_not_active"
    assert result is None
    assert dispatched == []
    assert log.snapshot()[-1]["event"] == "federated_action_outcome"
    assert log.snapshot()[-1]["outcome"] == "principal_agent_binding_rejected"


def test_federated_action_requires_binding_registry_dependency(tmp_path):
    from core.federated_action_gate import FederatedActionGate

    gate, _, _, _, _, _, _, _, _ = _setup(tmp_path)
    try:
        FederatedActionGate(
            gate._gate, gate._principals, binding_registry=object(),
            local_policy_version="local-v1", audit_recorder=gate._audit,
        )
    except TypeError as exc:
        assert str(exc) == "principal_agent_binding_registry_required"
    else:
        raise AssertionError("missing binding enforcement must fail closed")


def test_binding_revocation_waits_for_inflight_local_dispatch_boundary(tmp_path):
    gate, agents, principals, agent, _action, _admission, _agent_grant, _principal_grant, _log = _setup(tmp_path)
    second_registry = SQLitePrincipalAgentBindingRegistry(
        gate._bindings.database_path,
        principal_registry=principals,
        agent_registry=agents,
    )
    entered = Event()
    release = Event()
    revoke_started = Event()

    def bounded_dispatch():
        entered.set()
        assert release.wait(timeout=5)
        return "dispatch-linearized-before-revocation"

    def revoke():
        revoke_started.set()
        second_registry.revoke_binding("tenant-1", agent.agent_id)
        return "revoked"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            dispatch_future = pool.submit(
                gate._bindings.with_active_binding,
                "tenant-1", agent.agent_id, bounded_dispatch,
            )
            assert entered.wait(timeout=5)
            revoke_future = pool.submit(revoke)
            assert revoke_started.wait(timeout=5)
            assert revoke_future.done() is False
            release.set()
            assert dispatch_future.result(timeout=5) == "dispatch-linearized-before-revocation"
            assert revoke_future.result(timeout=5) == "revoked"
        assert gate._bindings.is_agent_owned_by_principal("tenant-1", agent.agent_id) is False
    finally:
        release.set()
        second_registry = None



def test_identity_revocation_waits_for_inflight_federated_dispatch(tmp_path):
    gate, agents, principals, agent, action, admission, agent_grant, principal_grant, _log = _setup(tmp_path)
    entered = Event()
    release = Event()
    agent_revoke_started = Event()
    principal_revoke_started = Event()

    def bounded_executor():
        entered.set()
        assert release.wait(timeout=5)
        return "dispatch-linearized-before-identity-revocation"

    def revoke_agent():
        agent_revoke_started.set()
        agents.revoke(agent.agent_id)

    def revoke_principal():
        principal_revoke_started.set()
        principals.revoke("tenant-1")

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            dispatch_future = pool.submit(
                _dispatch, gate, agent, action, admission,
                agent_grant, principal_grant, bounded_executor,
            )
            assert entered.wait(timeout=5)
            agent_revoke_future = pool.submit(revoke_agent)
            principal_revoke_future = pool.submit(revoke_principal)
            assert agent_revoke_started.wait(timeout=5)
            assert principal_revoke_started.wait(timeout=5)
            assert agent_revoke_future.done() is False
            assert principal_revoke_future.done() is False

            release.set()
            decision, result = dispatch_future.result(timeout=5)
            assert decision.allowed is True
            assert result == "dispatch-linearized-before-identity-revocation"
            agent_revoke_future.result(timeout=5)
            principal_revoke_future.result(timeout=5)

        assert agents.is_revoked(agent.agent_id) is True
        assert principals.is_revoked("tenant-1") is True
    finally:
        release.set()



def test_binding_revocation_waits_for_inflight_federated_dispatch(tmp_path):
    gate, agents, principals, agent, action, admission, agent_grant, principal_grant, _log = _setup(tmp_path)
    second_registry = SQLitePrincipalAgentBindingRegistry(
        gate._bindings.database_path,
        principal_registry=principals,
        agent_registry=agents,
    )
    entered = Event()
    release = Event()
    revoke_started = Event()

    def bounded_executor():
        entered.set()
        assert release.wait(timeout=5)
        return "federated-dispatch-linearized-before-binding-revocation"

    def revoke_binding():
        revoke_started.set()
        second_registry.revoke_binding("tenant-1", agent.agent_id)
        return "revoked"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            dispatch_future = pool.submit(
                _dispatch, gate, agent, action, admission,
                agent_grant, principal_grant, bounded_executor,
            )
            assert entered.wait(timeout=5)
            revoke_future = pool.submit(revoke_binding)
            assert revoke_started.wait(timeout=5)
            assert revoke_future.done() is False

            release.set()
            decision, result = dispatch_future.result(timeout=5)
            assert decision.allowed is True
            assert result == "federated-dispatch-linearized-before-binding-revocation"
            assert revoke_future.result(timeout=5) == "revoked"

        assert gate._bindings.is_agent_owned_by_principal("tenant-1", agent.agent_id) is False
        assert agents.is_revoked(agent.agent_id) is False
        assert principals.is_revoked("tenant-1") is False
    finally:
        release.set()



def test_binding_revocation_tombstone_survives_registry_reopen(tmp_path):
    gate, agents, principals, agent, _action, _admission, _agent_grant, _principal_grant, _log = _setup(tmp_path)
    database_path = gate._bindings.database_path
    gate._bindings.revoke_binding("tenant-1", agent.agent_id)

    reopened = SQLitePrincipalAgentBindingRegistry(
        database_path,
        principal_registry=principals,
        agent_registry=agents,
    )
    assert reopened.is_agent_owned_by_principal("tenant-1", agent.agent_id) is False
    try:
        reopened.bind("tenant-1", agent.agent_id)
    except PermissionError as exc:
        assert str(exc) == "principal_agent_binding_permanently_revoked"
    else:
        raise AssertionError("revoked principal-agent binding must not be recreated")

    assert agents.is_revoked(agent.agent_id) is False
    assert principals.is_revoked("tenant-1") is False



def test_concurrent_provisioning_cannot_assign_one_agent_to_two_principals(tmp_path):
    gate, agents, principals, _agent, _action, _admission, _agent_grant, _principal_grant, _log = _setup(tmp_path)
    second_agent, _ = AgentIdentityAuthority.generate("agent-2")
    agents.register(second_agent)

    second_key = Ed25519PrivateKey.generate()
    second_public = second_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    principals.register(PrincipalIdentity("tenant-2", second_public))

    first_registry = SQLitePrincipalAgentBindingRegistry(
        gate._bindings.database_path,
        principal_registry=principals,
        agent_registry=agents,
    )
    second_registry = SQLitePrincipalAgentBindingRegistry(
        gate._bindings.database_path,
        principal_registry=principals,
        agent_registry=agents,
    )
    start = Barrier(2)

    def attempt(registry, principal_id):
        start.wait(timeout=5)
        try:
            registry.bind(principal_id, "agent-2")
            return ("bound", principal_id)
        except PermissionError:
            return ("rejected", principal_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda args: attempt(*args),
            ((first_registry, "tenant-1"), (second_registry, "tenant-2")),
        ))

    assert sorted(status for status, _principal in results) == ["bound", "rejected"]
    active_owners = [
        principal_id for principal_id in ("tenant-1", "tenant-2")
        if first_registry.is_agent_owned_by_principal(principal_id, "agent-2")
    ]
    assert len(active_owners) == 1
    assert active_owners[0] == next(
        principal_id for status, principal_id in results if status == "bound"
    )


def _hold_active_binding_in_child(registry, entered, release, results):
    try:
        outcome = registry.with_active_binding(
            "tenant-1", "agent-1",
            lambda: (entered.set(), release.wait(10), "dispatch-completed")[-1],
        )
        results.put(("dispatch", outcome))
    except Exception as exc:
        results.put(("dispatch-error", type(exc).__name__))


def _revoke_binding_in_child(registry, attempting, results):
    attempting.set()
    try:
        registry.revoke_binding("tenant-1", "agent-1")
        results.put(("revoke", "completed"))
    except Exception as exc:
        results.put(("revoke-error", type(exc).__name__))


def test_independent_process_revocation_waits_for_active_binding_callback(tmp_path):
    from multiprocessing import get_all_start_methods, get_context
    from queue import Empty

    if "fork" not in get_all_start_methods():
        pytest.skip("requires POSIX fork for independent process SQLite test")

    gate, _agents, _principals, _agent, _action, _admission, _agent_grant, _principal_grant, _log = _setup(tmp_path)
    registry = gate._bindings
    context = get_context("fork")
    entered = context.Event()
    release = context.Event()
    attempting = context.Event()
    results = context.Queue()
    dispatch_process = context.Process(
        target=_hold_active_binding_in_child,
        args=(registry, entered, release, results),
    )
    revoke_process = context.Process(
        target=_revoke_binding_in_child,
        args=(registry, attempting, results),
    )
    dispatch_process.start()
    try:
        assert entered.wait(10), "dispatch callback did not acquire active binding"
        revoke_process.start()
        assert attempting.wait(10), "revocation process did not begin"
        with pytest.raises(Empty):
            results.get(timeout=0.2)
        release.set()
        first = results.get(timeout=10)
        second = results.get(timeout=10)
        dispatch_process.join(timeout=10)
        revoke_process.join(timeout=10)
    finally:
        release.set()
        for process in (dispatch_process, revoke_process):
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()

    assert {first[0], second[0]} == {"dispatch", "revoke"}
    assert ("dispatch", "dispatch-completed") in (first, second)
    assert ("revoke", "completed") in (first, second)
    assert dispatch_process.exitcode == 0
    assert revoke_process.exitcode == 0
    assert registry.is_agent_owned_by_principal("tenant-1", "agent-1") is False
