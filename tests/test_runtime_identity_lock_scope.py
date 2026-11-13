from threading import Event, Thread

from core.identity import AgentIdentityAuthority, IdentityRegistry
from noryx7_runtime.attestation import Ed25519AttestationSigner
from noryx7_runtime.contracts import ExecutionStatus, Intent, PlanStep
from noryx7_runtime.engine import RuntimeEngine


class RevokingAdapter:
    agent_id = "adapter-agent"

    def __init__(self, registry):
        self.registry = registry
        self.revocation_completed = Event()

    def execute(self, envelope):
        def revoke():
            self.registry.revoke(self.agent_id)
            self.revocation_completed.set()

        thread = Thread(target=revoke)
        thread.start()
        completed = self.revocation_completed.wait(timeout=1.0)
        thread.join(timeout=1.0)
        if not completed:
            raise AssertionError("identity_registry_lock_held_during_external_execution")
        return {"executed": True}


def test_identity_registry_lock_is_released_before_adapter_side_effect():
    registry = IdentityRegistry()
    identity, private_key = AgentIdentityAuthority.generate("adapter-agent")
    registry.register(identity)
    adapter = RevokingAdapter(registry)
    engine = RuntimeEngine(
        adapter=adapter,
        attestation_signer=Ed25519AttestationSigner(private_key),
        identity_registry=registry,
    )

    result = engine.execute(
        Intent("execute a test action", "principal-1"),
        [PlanStep("step-1", "local.test", "local", {})],
        verifier=lambda envelope, output: output == {"executed": True},
    )
    assert adapter.revocation_completed.is_set()
    assert result.status is ExecutionStatus.SUCCEEDED
    assert not registry.is_trusted(identity)
