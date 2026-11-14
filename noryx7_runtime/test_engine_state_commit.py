from .attestation import Ed25519AttestationSigner, Ed25519AttestationVerifier, attestation_digest, signed_attestation
from .contracts import Attestation, ExecutionStatus, Intent, PlanStep
from .engine import RuntimeEngine
from .state import StateJournal


def test_engine_commits_verified_attestation_to_state_journal():
    signer = Ed25519AttestationSigner.generate()
    verifier = Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes)
    journal = StateJournal(verifier=verifier, runtime_id="runtime-test")
    engine = RuntimeEngine(runtime_id="runtime-test", state_journal=journal, attestation_signer=signer)

    result = engine.execute(
        Intent("run", "user"),
        [PlanStep("a", "tool.call", "target", {})],
        executor=lambda action: {"ok": True},
        verifier=lambda action, output: output["ok"],
    )

    assert result.status is ExecutionStatus.SUCCEEDED
    entries = journal.snapshot()
    assert len(entries) == 1
    assert entries[0].execution_id == result.execution_id
    assert entries[0].runtime_id == "runtime-test"


class RejectingVerifier:
    def verify(self, attestation, signature):
        return False


def test_state_commit_failure_cannot_report_success():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=RejectingVerifier(), runtime_id="runtime-test")
    engine = RuntimeEngine(runtime_id="runtime-test", state_journal=journal, attestation_signer=signer)

    result = engine.execute(
        Intent("run", "user"),
        [PlanStep("a", "tool.call", "target", {})],
        executor=lambda action: "ok",
        verifier=lambda action, output: True,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error == "PermissionError"
    assert journal.snapshot() == ()


def test_journal_preserves_provenance_when_rebuilding_chain_digest():
    signer = Ed25519AttestationSigner.generate()
    verifier = Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes)
    journal = StateJournal(verifier=verifier, runtime_id="runtime-test")
    first = signed_attestation(Attestation(
        execution_id="exec", principal_id="user", step_id="one", agent_id="agent",
        agent_key_fingerprint=__import__("hashlib").sha256(signer.public_key_bytes).hexdigest(),
        action_digest="1" * 64, output_digest="2" * 64, verified=True,
        detail="verified", runtime_id="runtime-test", provenance_digest="3" * 64,
        provenance_seal=b"s" * 32,
    ), signer)
    journal.append(first)
    second = signed_attestation(Attestation(
        execution_id="exec", principal_id="user", step_id="two", agent_id="agent",
        agent_key_fingerprint=first.agent_key_fingerprint,
        action_digest="4" * 64, output_digest="5" * 64, verified=True,
        detail="verified", previous_attestation_digest=attestation_digest(first),
        runtime_id="runtime-test", provenance_digest="6" * 64, provenance_seal=b"t" * 32,
    ), signer)
    journal.append(second)
    assert len(journal.snapshot()) == 2
