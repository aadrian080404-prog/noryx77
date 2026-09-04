import threading
import time

import pytest

from core.identity import AgentIdentityAuthority, IdentityRegistry

from .adapters import CapabilityAdapter
from .attestation import Ed25519AttestationSigner, verify_attestation
from .capabilities import Capability, CapabilityBroker
from .contracts import ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine


def step(step_id, deps=(), action_type="tool.call"):
    return PlanStep(step_id, action_type, "target", {"step": step_id}, tuple(deps))


def capability_adapter(seen=None, agent_id="agent-1"):
    return CapabilityAdapter(
        CapabilityBroker({
            "tool": Capability("tool", frozenset({"tool.call"}), lambda action: seen.append(action) if seen is not None else "ok")
        }),
        agent_id=agent_id,
    )


def test_dependencies_are_executed_in_deterministic_topological_order():
    seen = []
    engine = RuntimeEngine()
    result = engine.execute(
        Intent("run", "user"),
        [step("c", ("a", "b")), step("b"), step("a")],
        executor=lambda action: seen.append(action.step_id) or action.step_id,
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert seen == ["a", "b", "c"]


def test_capability_adapter_requires_signed_attestation():
    seen = []
    broker = CapabilityBroker({
        "tool": Capability("tool", frozenset({"tool.call"}), lambda action: seen.append(action) or "ok")
    })
    signer = Ed25519AttestationSigner.generate()
    result = RuntimeEngine(adapter=CapabilityAdapter(broker, agent_id="agent-1"), attestation_signer=signer).execute(
        Intent("run", "user"),
        [step("a")],
        verifier=lambda action, output: output == "ok",
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert len(seen) == 1
    assert result.attestations[0].agent_id == "agent-1"
    assert verify_attestation(result.attestations[0], signer)
    assert len(result.attestations[0].agent_key_fingerprint) == 64


def test_identity_bound_adapter_requires_registered_signing_key():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    signer = Ed25519AttestationSigner(private_key)
    result = RuntimeEngine(
        adapter=capability_adapter(agent_id="agent-1"),
        attestation_signer=signer,
        identity_registry=registry,
    ).execute(
        Intent("run", "user"), [step("a")], verifier=lambda action, output: True
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    registry.revoke("agent-1")
    assert not registry.is_trusted(identity)


def test_identity_bound_adapter_rejects_replaced_public_key():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    replacement, replacement_key = AgentIdentityAuthority.generate("agent-1")
    signer = Ed25519AttestationSigner(replacement_key)
    with pytest.raises(PermissionError, match="adapter identity"):
        RuntimeEngine(
            adapter=capability_adapter(agent_id="agent-1"),
            attestation_signer=signer,
            identity_registry=registry,
        )
    assert private_key is not None and replacement.public_key != identity.public_key


def test_revocation_before_runtime_dispatch_fails_closed():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    registry.revoke("agent-1")
    called = []
    signer = Ed25519AttestationSigner(private_key)
    engine = object.__new__(RuntimeEngine)
    with pytest.raises(PermissionError, match="adapter identity"):
        RuntimeEngine(
            adapter=capability_adapter(called, agent_id="agent-1"),
            attestation_signer=signer,
            identity_registry=registry,
        )
    assert called == []


def test_revocation_cannot_interleave_with_effect_dispatch():
    identity, private_key = AgentIdentityAuthority.generate("agent-1")
    registry = IdentityRegistry()
    registry.register(identity)
    signer = Ed25519AttestationSigner(private_key)
    started = threading.Event()
    release = threading.Event()
    called = []

    class BlockingAdapter:
        agent_id = "agent-1"

        def execute(self, envelope):
            called.append(envelope.step_id)
            started.set()
            assert release.wait(2)
            return "ok"

    engine = RuntimeEngine(
        adapter=BlockingAdapter(),
        attestation_signer=signer,
        identity_registry=registry,
    )
    result = []

    def run():
        result.append(engine.execute(
            Intent("run", "user"), [step("a")], verifier=lambda action, output: True
        ))

    worker = threading.Thread(target=run)
    worker.start()
    assert started.wait(2)

    revoke_done = threading.Event()

    def revoke():
        registry.revoke("agent-1")
        revoke_done.set()

    revoker = threading.Thread(target=revoke)
    revoker.start()
    time.sleep(0.05)
    assert not revoke_done.is_set()
    release.set()
    worker.join(2)
    revoker.join(2)

    assert len(result) == 1
    assert result[0].status is ExecutionStatus.SUCCEEDED
    assert called == ["a"]
    assert revoke_done.is_set()
    assert not registry.is_trusted(identity)


def test_adapter_without_attestation_signer_is_rejected_at_construction():
    with pytest.raises(ValueError, match="attestation_signer"):
        RuntimeEngine(adapter=capability_adapter())


def test_adapter_rejects_unregistered_effect_type_before_execution():
    result = RuntimeEngine(
        adapter=CapabilityAdapter(CapabilityBroker(), agent_id="agent-1"),
        attestation_signer=Ed25519AttestationSigner.generate(),
    ).execute(
        Intent("run", "user"),
        [step("a")],
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "LookupError"


def test_budget_rejects_before_any_execution():
    called = []
    result = RuntimeEngine(max_actions=1).execute(
        Intent("run", "user"),
        [step("a"), step("b")],
        executor=lambda action: called.append(action.step_id),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "action_budget_exceeded"
    assert called == []


def test_failed_verification_never_commits():
    commits = []
    result = RuntimeEngine(
        attestation_signer=Ed25519AttestationSigner.generate(),
    ).execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: "unsafe",
        verifier=lambda action, output: False,
        committer=lambda *args: commits.append(args),
    )
    assert result.status is ExecutionStatus.REJECTED
    assert result.error == "result_verification_failed"
    assert commits == []


def test_executor_exception_fails_closed():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: (_ for _ in ()).throw(RuntimeError("boom")),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "RuntimeError"


def test_committer_exception_does_not_report_success():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: "ok",
        verifier=lambda action, output: True,
        committer=lambda *args: (_ for _ in ()).throw(RuntimeError("storage")),
    )
    assert result.status is ExecutionStatus.FAILED


def test_non_json_output_fails_closed():
    result = RuntimeEngine().execute(
        Intent("run", "user"),
        [step("a")],
        executor=lambda action: object(),
        verifier=lambda action, output: True,
    )
    assert result.status is ExecutionStatus.FAILED
    assert result.error in {"TypeError", "ValueError"}


def test_missing_dependency_and_cycle_fail_closed():
    engine = RuntimeEngine()
    with pytest.raises(ValueError, match="missing dependency"):
        engine.execute(Intent("run", "user"), [step("a", ("missing",))], executor=lambda a: None, verifier=lambda a, o: True)
    with pytest.raises(ValueError, match="cyclic"):
        engine.execute(Intent("run", "user"), [step("a", ("b",)), step("b", ("a",))], executor=lambda a: None, verifier=lambda a, o: True)
