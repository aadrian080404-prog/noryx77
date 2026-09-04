import hashlib

import pytest

from .attestation import Ed25519AttestationSigner, signed_attestation, attestation_digest
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import JournalEntry, StateJournal


def attestation(signer, execution="exec", step="a", principal="user", runtime_id=""):
    return signed_attestation(Attestation(
        execution_id=execution,
        principal_id=principal,
        step_id=step,
        agent_id="adapter",
        agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
        action_digest=hashlib.sha256((execution + ":" + step + ":action").encode()).hexdigest(),
        output_digest=hashlib.sha256((execution + ":" + step + ":output").encode()).hexdigest(),
        verified=True,
        detail="verified",
        runtime_id=runtime_id,
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
    duplicate = JournalEntry(1, first.execution_id, first.principal_id, first.step_id, first.agent_id, first.agent_key_fingerprint, first.action_digest, first.output_digest, first.signature)
    journal._entries.append(duplicate)
    with pytest.raises(RecoveryError, match="duplicate committed step"):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_non_monotonic_sequence():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = journal.append(attestation(signer, "exec", "a"))
    second = journal.append(attestation(signer, "exec", "b"))
    journal._entries = [second, first]
    with pytest.raises(RecoveryError, match="strictly increasing"):
        RuntimeRecovery(journal).recover("exec")


def test_recovery_rejects_invalid_execution_id():
    signer = Ed25519AttestationSigner.generate()
    with pytest.raises(ValueError, match="invalid execution identity"):
        RuntimeRecovery(StateJournal(verifier=signer)).recover("")


def test_recovery_preserves_provenance_binding_and_chain_digest():
    signer = Ed25519AttestationSigner.generate()
    verifier = signer
    journal = StateJournal(verifier=verifier, runtime_id="runtime-1")
    first = signed_attestation(Attestation(
        execution_id="exec", principal_id="user", step_id="a", agent_id="adapter",
        agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
        action_digest="a" * 64, output_digest="b" * 64, verified=True, detail="verified",
        runtime_id="runtime-1", provenance_digest="c" * 64, provenance_seal=b"s" * 32,
    ), signer)
    journal.append(first)
    recovered = RuntimeRecovery(journal).recover("exec")
    assert recovered[0].provenance_digest == first.provenance_digest
    assert recovered[0].provenance_seal == first.provenance_seal
    assert recovered[0].signature == first.signature
    assert attestation_digest(Attestation(
        execution_id=recovered[0].execution_id, principal_id=recovered[0].principal_id,
        step_id=recovered[0].step_id, agent_id=recovered[0].agent_id,
        agent_key_fingerprint=recovered[0].agent_key_fingerprint, action_digest=recovered[0].action_digest,
        output_digest=recovered[0].output_digest, verified=True, detail="verified", signature=recovered[0].signature,
        previous_attestation_digest=recovered[0].previous_attestation_digest, runtime_id=recovered[0].runtime_id,
        provenance_digest=recovered[0].provenance_digest, provenance_seal=recovered[0].provenance_seal,
    )) == attestation_digest(first)
