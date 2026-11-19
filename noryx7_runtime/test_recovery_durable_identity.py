import hashlib

import pytest

from core.identity import AgentIdentity
from core.sqlite_agent_identity_registry import SQLiteAgentIdentityRegistry
from .attestation import Ed25519AttestationSigner, signed_attestation
from .contracts import Attestation
from .recovery import RecoveryError, RuntimeRecovery
from .state import StateJournal


def _signed_entry(signer):
    return signed_attestation(
        Attestation(
            execution_id="execution-1",
            principal_id="principal-1",
            step_id="step-1",
            agent_id="agent-1",
            agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
            action_digest=hashlib.sha256(b"action").hexdigest(),
            output_digest=hashlib.sha256(b"output").hexdigest(),
            verified=True,
            detail="verified",
        ),
        signer,
    )


def test_state_journal_and_recovery_accept_durable_identity_registry(tmp_path):
    signer = Ed25519AttestationSigner.generate()
    registry = SQLiteAgentIdentityRegistry(tmp_path / "identity.db")
    registry.register(AgentIdentity("agent-1", signer.public_key_bytes))
    try:
        journal = StateJournal(verifier=signer, identity_registry=registry)
        journal.append(_signed_entry(signer))

        recovered = RuntimeRecovery(journal).recover("execution-1")

        assert len(recovered) == 1
        assert recovered[0].agent_id == "agent-1"
    finally:
        registry.close()


def test_runtime_recovery_rejects_identity_revoked_after_commit(tmp_path):
    signer = Ed25519AttestationSigner.generate()
    registry = SQLiteAgentIdentityRegistry(tmp_path / "identity.db")
    registry.register(AgentIdentity("agent-1", signer.public_key_bytes))
    try:
        journal = StateJournal(verifier=signer, identity_registry=registry)
        journal.append(_signed_entry(signer))

        registry.revoke("agent-1")

        with pytest.raises(RecoveryError, match="attestation verification failed"):
            RuntimeRecovery(journal).recover("execution-1")
    finally:
        registry.close()


def test_state_journal_rejects_non_registry_objects():
    signer = Ed25519AttestationSigner.generate()
    with pytest.raises(TypeError, match="live trust checks"):
        StateJournal(verifier=signer, identity_registry=object())
