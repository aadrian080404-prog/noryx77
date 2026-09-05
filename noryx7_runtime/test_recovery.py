import hashlib

import pytest

from .attestation import Ed25519AttestationSigner, signed_attestation
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import JournalEntry, StateJournal


def attestation(signer, execution="exec", step="a", principal="user"):
    return signed_attestation(Attestation(
        execution_id=execution,
        principal_id=principal,
        step_id=step,
        agent_id="adapter",
        agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
        action_digest=hashlib.sha256(("action:" + execution + ":" + step).encode()).hexdigest(),
        output_digest=hashlib.sha256(("output:" + execution + ":" + step).encode()).hexdigest(),
        verified=True,
        detail="verified",
    ), signer)


def test_recovery_returns_only_committed_execution_entries():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    journal.append(attestation(signer, "one", "a"))
    journal.append(attestation(signer, "two", "b"))
    journal.append(attestation(signer, "one", "c"))

    recovered = RuntimeRecovery(journal).recover("one")
    assert [entry.step_id for entry in recovered] == ["a", "c"]
    assert all(entry.execution_id == "one" for entry in recovered)


def test_recovery_rejects_duplicate_step_commits():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = journal.append(attestation(signer, "exec", "a"))
    duplicate = JournalEntry(
        1, first.execution_id, first.principal_id, first.step_id, first.agent_id,
        first.agent_key_fingerprint, first.action_digest, first.output_digest, first.signature,
    )
    journal._entries.append(duplicate)
    with pytest.raises(RecoveryError, match="duplicate committed step"):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_non_monotonic_sequence():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = journal.append(attestation(signer, "exec", "a"))
    second = journal.append(attestation(signer, "exec", "b"))
    journal._entries = [second, first]
    with pytest.raises(RecoveryError):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_invalid_execution_id():
    signer = Ed25519AttestationSigner.generate()
    with pytest.raises(ValueError, match="invalid execution identity"):
        RuntimeRecovery(StateJournal(verifier=signer)).recover("")
