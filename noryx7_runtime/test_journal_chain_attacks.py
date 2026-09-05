import hashlib

import pytest

from .attestation import Ed25519AttestationSigner, attestation_digest, signed_attestation
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import StateJournal


def make_attestation(signer, *, execution_id="exec-1", principal_id="principal-1", step_id="step-1", previous="0" * 64, action="a" * 64):
    return signed_attestation(
        Attestation(
            execution_id=execution_id,
            principal_id=principal_id,
            step_id=step_id,
            agent_id="agent-1",
            agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
            action_digest=action,
            output_digest="b" * 64,
            verified=True,
            detail="verified",
            previous_attestation_digest=previous,
        ),
        signer,
    )


def test_append_rejects_nonzero_first_chain_link():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    forged = make_attestation(signer, previous="1" * 64)
    with pytest.raises(ValueError, match="chain link mismatch"):
        journal.append(forged)


def test_append_rejects_fork_from_same_previous_digest():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = make_attestation(signer)
    journal.append(first)
    previous = attestation_digest(first)
    second = make_attestation(signer, step_id="step-2", previous=previous, action="c" * 64)
    journal.append(second)
    fork = make_attestation(signer, step_id="step-3", previous=previous, action="d" * 64)
    with pytest.raises(ValueError, match="chain link mismatch"):
        journal.append(fork)


def test_recovery_rejects_reordered_entries():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = make_attestation(signer, step_id="step-1")
    journal.append(first)
    second = make_attestation(signer, step_id="step-2", previous=attestation_digest(first), action="c" * 64)
    journal.append(second)
    journal._entries = [journal.snapshot()[1], journal.snapshot()[0]]
    with pytest.raises(RecoveryError):
        RuntimeRecovery(journal).recover("exec-1")


def test_recovery_rejects_replaced_signed_entry():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    first = make_attestation(signer)
    journal.append(first)
    second = make_attestation(signer, step_id="step-2", previous=attestation_digest(first), action="c" * 64)
    journal.append(second)
    original = journal.snapshot()[0]
    replacement = make_attestation(signer, step_id="step-1", action="e" * 64)
    replacement_entry = journal._entries[0].__class__(
        original.sequence,
        replacement.execution_id,
        replacement.principal_id,
        replacement.step_id,
        replacement.agent_id,
        replacement.agent_key_fingerprint,
        replacement.action_digest,
        replacement.output_digest,
        replacement.signature,
        replacement.previous_attestation_digest,
    )
    journal._entries[0] = replacement_entry
    with pytest.raises(RecoveryError):
        RuntimeRecovery(journal).recover("exec-1")


def test_journal_binds_execution_to_one_principal():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    journal.append(make_attestation(signer, principal_id="principal-1"))
    with pytest.raises(PermissionError, match="execution principal mismatch"):
        journal.append(make_attestation(
            signer,
            principal_id="principal-2",
            step_id="step-2",
            previous=journal._entry_digest(journal.snapshot()[0]),
            action="c" * 64,
        ))


def test_interleaved_execution_chains_remain_independent():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer)
    a1 = make_attestation(signer, execution_id="exec-a", step_id="a1")
    b1 = make_attestation(signer, execution_id="exec-b", step_id="b1")
    journal.append(a1)
    journal.append(b1)
    a2 = make_attestation(signer, execution_id="exec-a", step_id="a2", previous=attestation_digest(a1), action="c" * 64)
    b2 = make_attestation(signer, execution_id="exec-b", step_id="b2", previous=attestation_digest(b1), action="d" * 64)
    journal.append(a2)
    journal.append(b2)
    assert len(RuntimeRecovery(journal).recover("exec-a")) == 2
    assert len(RuntimeRecovery(journal).recover("exec-b")) == 2
