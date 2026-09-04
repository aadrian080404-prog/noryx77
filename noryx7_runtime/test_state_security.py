import hashlib
import threading

import pytest

from core.identity import AgentIdentityAuthority, IdentityRegistry

from .attestation import Ed25519AttestationSigner, IdentityBoundAttestationVerifier, signed_attestation, attestation_digest
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import StateJournal


def make_attestation(signer):
    return signed_attestation(Attestation(
        execution_id="exec-1", principal_id="principal-1", step_id="step-1", agent_id="agent-1",
        agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(), action_digest="a" * 64,
        output_digest="b" * 64, verified=True, detail="verified",
    ), signer)


def test_signed_journal_requires_a_verifier():
    with pytest.raises(ValueError, match="verifier"): StateJournal()


def test_journal_rejects_duplicate_execution_step():
    signer = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer)
    value = make_attestation(signer); journal.append(value)
    with pytest.raises(ValueError, match="duplicate execution step"): journal.append(value)


def test_journal_rejects_unsigned_commit():
    signer = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer)
    unsigned = Attestation(execution_id="e", principal_id="p", step_id="s", agent_id="a", agent_key_fingerprint="c" * 64, action_digest="a" * 64, output_digest="b" * 64, verified=True)
    with pytest.raises(PermissionError, match="unsigned"): journal.append(unsigned)


def test_journal_rejects_signature_from_different_key_at_commit():
    signer = Ed25519AttestationSigner.generate(); other = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer)
    with pytest.raises(PermissionError, match="invalid attestation signature"): journal.append(make_attestation(other))


def test_registry_commit_rejects_substituted_key_fingerprint():
    identity, private_key = AgentIdentityAuthority.generate("agent-1"); registry = IdentityRegistry(); registry.register(identity)
    signer = Ed25519AttestationSigner(private_key); journal = StateJournal(verifier=signer, identity_registry=registry)
    forged = make_attestation(signer)
    forged = forged.__class__(execution_id=forged.execution_id, principal_id=forged.principal_id, step_id=forged.step_id, agent_id=forged.agent_id, agent_key_fingerprint="f" * 64, action_digest=forged.action_digest, output_digest=forged.output_digest, verified=forged.verified, detail=forged.detail, signature=b"x" * 64)
    with pytest.raises(PermissionError, match="fingerprint"): journal.append(forged)


def test_recovery_rejects_tampered_signed_entry():
    signer = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer); journal.append(make_attestation(signer)); entry = journal.snapshot()[0]
    journal._entries[0] = type(entry)(entry.sequence, entry.execution_id, entry.principal_id, entry.step_id, entry.agent_id, entry.agent_key_fingerprint, entry.action_digest, "c" * 64, entry.signature)
    with pytest.raises(RecoveryError, match="attestation verification failed"): RuntimeRecovery(journal).recover("exec-1")


def test_recovery_rejects_signature_from_different_key():
    signer = Ed25519AttestationSigner.generate(); other = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer); journal.append(make_attestation(signer))
    with pytest.raises(RecoveryError, match="attestation verification failed"): RuntimeRecovery(journal, other).recover("exec-1")


def test_recovery_rejects_duplicate_step_even_without_mutating_journal_api():
    signer = Ed25519AttestationSigner.generate(); journal = StateJournal(verifier=signer); first = make_attestation(signer); journal.append(first)
    second = signed_attestation(Attestation(execution_id="exec-1", principal_id="principal-1", step_id="step-2", agent_id="agent-1", agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(), action_digest="c" * 64, output_digest="d" * 64, verified=True, detail="verified", previous_attestation_digest=attestation_digest(first)), signer)
    entry = journal.append(second); journal._entries = [journal.snapshot()[0], entry, entry]
    with pytest.raises(RecoveryError, match="duplicate committed step"): RuntimeRecovery(journal).recover("exec-1")


def test_revocation_is_linearized_against_attestation_commit():
    identity, private_key = AgentIdentityAuthority.generate("agent-1"); registry = IdentityRegistry(); registry.register(identity); signer = Ed25519AttestationSigner(private_key); verifier = IdentityBoundAttestationVerifier(registry); journal = StateJournal(verifier=verifier, identity_registry=registry); value = make_attestation(signer); entered = threading.Event(); release = threading.Event()
    class BlockingVerifier:
        def verify(self, value, signature): entered.set(); assert release.wait(2); return verifier.verify(value, signature)
    journal._verifier = BlockingVerifier(); result = []
    def commit(): result.append(journal.append(value))
    commit_thread = threading.Thread(target=commit); commit_thread.start(); assert entered.wait(2); revoke_thread = threading.Thread(target=lambda: registry.revoke("agent-1")); revoke_thread.start(); assert revoke_thread.is_alive(); release.set(); commit_thread.join(2); revoke_thread.join(2)
    assert len(result) == 1; assert not registry.is_trusted(identity); assert len(journal.snapshot()) == 1


def test_recovery_rejects_revoked_identity_even_when_signature_is_valid():
    identity, private_key = AgentIdentityAuthority.generate("agent-1"); registry = IdentityRegistry(); registry.register(identity); signer = Ed25519AttestationSigner(private_key); verifier = IdentityBoundAttestationVerifier(registry); journal = StateJournal(verifier=verifier, identity_registry=registry); journal.append(make_attestation(signer)); registry.revoke("agent-1")
    with pytest.raises(RecoveryError, match="attestation verification failed"): RuntimeRecovery(journal).recover("exec-1")


def test_recovery_rejects_current_key_replacement_even_with_old_valid_signature():
    identity, private_key = AgentIdentityAuthority.generate("agent-1"); replacement, replacement_key = AgentIdentityAuthority.generate("agent-1"); registry = IdentityRegistry(); registry.register(identity); signer = Ed25519AttestationSigner(private_key); verifier = IdentityBoundAttestationVerifier(registry); journal = StateJournal(verifier=verifier, identity_registry=registry); journal.append(make_attestation(signer)); registry.revoke("agent-1"); registry.register(replacement)
    assert replacement.public_key != identity.public_key
    with pytest.raises(RecoveryError, match="attestation verification failed"): RuntimeRecovery(journal).recover("exec-1")
    assert replacement_key is not None
