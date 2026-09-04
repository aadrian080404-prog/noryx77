from __future__ import annotations

import hashlib
from core.identity import IdentityRegistry
from .attestation import AttestationVerifier, attestation_digest
from .contracts import Attestation
from .state import JournalEntry, StateJournal


class RecoveryError(ValueError):
    """Raised when the persisted runtime journal violates its invariants."""


class RuntimeRecovery:
    def __init__(self, journal: StateJournal, verifier: AttestationVerifier | None = None, identity_registry: IdentityRegistry | None = None):
        if not isinstance(journal, StateJournal):
            raise TypeError("journal must be a StateJournal")
        effective_verifier = verifier if verifier is not None else journal.verifier
        effective_registry = identity_registry if identity_registry is not None else journal.identity_registry
        if effective_registry is not None and not isinstance(effective_registry, IdentityRegistry):
            raise TypeError("identity_registry must be an IdentityRegistry")
        if journal.require_signatures and effective_verifier is None:
            raise ValueError("signed journal recovery requires an attestation verifier")
        if effective_verifier is not None and not callable(getattr(effective_verifier, "verify", None)):
            raise TypeError("verifier must expose verify")
        self._journal = journal
        self._verifier = effective_verifier
        self._identity_registry = effective_registry

    def recover(self, execution_id: str):
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("invalid execution identity")
        entries = tuple(e for e in self._journal.snapshot() if e.execution_id == execution_id)
        self._validate(entries, self._verifier, self._identity_registry, self._journal.runtime_id)
        return entries

    @staticmethod
    def _validate(entries, verifier=None, identity_registry=None, runtime_id=None):
        previous_sequence = -1
        previous_digest = "0" * 64
        seen_steps = set()
        for entry in entries:
            if not isinstance(entry, JournalEntry):
                raise RecoveryError("invalid journal entry")
            if entry.step_id in seen_steps:
                raise RecoveryError("duplicate committed step")
            # Journal sequence numbers are global to the journal, not local to an
            # execution chain. Recovery filters one execution before validation,
            # so its first sequence may legitimately be > 0 when executions are
            # interleaved in the same journal.
            if entry.sequence <= previous_sequence:
                raise RecoveryError("journal sequence is not strictly increasing")
            if runtime_id is not None and entry.runtime_id != runtime_id:
                raise RecoveryError("journal runtime identity mismatch")
            fields = (entry.execution_id, entry.principal_id, entry.step_id, entry.agent_id, entry.agent_key_fingerprint, entry.action_digest, entry.output_digest, entry.previous_attestation_digest)
            if any(not isinstance(v, str) or not v for v in fields):
                raise RecoveryError("incomplete journal entry")
            for digest in (entry.agent_key_fingerprint, entry.previous_attestation_digest):
                if len(digest) != 64:
                    raise RecoveryError("invalid journal digest")
                try:
                    int(digest, 16)
                except ValueError as exc:
                    raise RecoveryError("invalid journal digest") from exc
            for digest in (entry.action_digest, entry.output_digest):
                if len(digest) != 64:
                    raise RecoveryError("invalid journal digest")
            if not isinstance(entry.signature, bytes) or len(entry.signature) != 64:
                raise RecoveryError("invalid attestation signature")
            if verifier is None:
                raise RecoveryError("attestation verifier required")
            attestation = Attestation(
                execution_id=entry.execution_id,
                principal_id=entry.principal_id,
                step_id=entry.step_id,
                agent_id=entry.agent_id,
                agent_key_fingerprint=entry.agent_key_fingerprint,
                action_digest=entry.action_digest,
                output_digest=entry.output_digest,
                verified=True,
                detail="verified",
                signature=entry.signature,
                previous_attestation_digest=entry.previous_attestation_digest,
                runtime_id=entry.runtime_id,
            )
            try:
                if identity_registry is not None:
                    valid = bool(identity_registry.with_trusted_identity(entry.agent_id, lambda identity: RuntimeRecovery._verify_with_identity(identity, attestation, entry.signature, verifier)))
                else:
                    valid = bool(verifier.verify(attestation, entry.signature))
            except Exception as exc:
                raise RecoveryError("attestation verification failed") from exc
            if not valid:
                raise RecoveryError("attestation verification failed")
            if runtime_id is not None or entry.previous_attestation_digest != "0" * 64:
                if entry.previous_attestation_digest != previous_digest:
                    raise RecoveryError("attestation verification failed: attestation chain is broken")
            previous_digest = attestation_digest(attestation)
            previous_sequence = entry.sequence
            seen_steps.add(entry.step_id)

    @staticmethod
    def _verify_with_identity(identity, attestation, signature, verifier):
        if hashlib.sha256(identity.public_key).hexdigest() != attestation.agent_key_fingerprint:
            return False
        return bool(verifier.verify(attestation, signature))
