from .attestation import Ed25519AttestationSigner, Ed25519AttestationVerifier
from .contracts import ExecutionStatus, Intent, PlanStep
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


def test_state_commit_failure_cannot_report_success():
    signer = Ed25519AttestationSigner.generate()
    verifier = Ed25519AttestationVerifier.from_public_key_bytes(signer.public_key_bytes)
    journal = StateJournal(verifier=verifier, runtime_id="runtime-test")
    engine = RuntimeEngine(runtime_id="runtime-other", state_journal=journal, attestation_signer=signer)

    result = engine.execute(
        Intent("run", "user"),
        [PlanStep("a", "tool.call", "target", {})],
        executor=lambda action: "ok",
        verifier=lambda action, output: True,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error == "ValueError"
    assert journal.snapshot() == ()
