import pytest

from .attestation import Ed25519AttestationSigner, signed_attestation
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import StateJournal


def make_attestation(signer):
    return signed_attestation(
        Attestation(
            execution_id="exec-1",
            principal_id="principal-1",
            step_id="step-1",
            agent_id="agent-1",
            action_digest="a" * 64,
            output_digest="b" * 64,
            verified=True,
            detail="verified",
        ),
        signer,
    )


def test_signed_journal_requires_a_verifier():
    with pytest.raises(ValueError, match="verifier"):
        StateJournal()


def test_journal_rejects_duplicate_execution_step():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    attestation = make_attestation(signer)
    journal.append(attestation)
    with pytest.raises(ValueError, match="duplicate execution step"):
        journal.append(attestation)


def test_journal_rejects_unsigned_commit():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    unsigned = Attestation("e", "p", "s", "a", "a" * 64, "b" * 64, True)
    with pytest.raises(PermissionError, match="unsigned"):
        journal.append(unsigned)


def test_journal_rejects_signature_from_different_key_at_commit():
    signer = Ed25519AttestationSigner.generate()
    other = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    with pytest.raises(PermissionError, match="invalid attestation signature"):
        journal.append(make_attestation(other))


def test_recovery_rejects_tampered_signed_entry():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    journal.append(make_attestation(signer))
    entry = journal.snapshot()[0]
    journal._entries[0] = type(entry)(
        entry.sequence, entry.execution_id, entry.principal_id, entry.step_id,
        entry.agent_id, entry.action_digest, "c" * 64, entry.signature
    )
    with pytest.raises(RecoveryError, match="attestation verification failed"):
        RuntimeRecovery(journal).recover("exec-1")


def test_recovery_rejects_signature_from_different_key():
    signer = Ed25519AttestationSigner.generate()
    other = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    journal.append(make_attestation(signer))
    with pytest.raises(RecoveryError, match="attestation verification failed"):
        RuntimeRecovery(journal, other).recover("exec-1")


def test_recovery_rejects_duplicate_step_even_without_mutating_journal_api():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = make_attestation(signer)
    journal.append(first)
    second = signed_attestation(Attestation(
        "exec-1", "principal-1", "step-2", "agent-1", "c" * 64, "d" * 64, True, "verified"
    ), signer)
    entry = journal.append(second)
    journal._entries = [journal.snapshot()[0], entry, entry]
    with pytest.raises(RecoveryError, match="duplicate committed step"):
        RuntimeRecovery(journal).recover("exec-1")
