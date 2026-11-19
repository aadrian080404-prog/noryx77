"""External checkpoint coordination for the durable federated action audit log.

The external anchor must be independently protected and pre-provisioned with
the domain-specific genesis checkpoint. This adapter only recovers one local
append that committed before a process crashed prior to anchor advancement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FederatedAuditCheckpoint:
    sequence: int
    digest: bytes

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.sequence, int)
            and not isinstance(self.sequence, bool)
            and self.sequence >= 0
            and isinstance(self.digest, bytes)
            and len(self.digest) == 32
        )


class ExternalFederatedAuditAnchor(Protocol):
    def read_checkpoint(self, namespace: str) -> FederatedAuditCheckpoint | None: ...

    def compare_and_advance(
        self,
        namespace: str,
        expected: FederatedAuditCheckpoint,
        next_checkpoint: FederatedAuditCheckpoint,
    ) -> bool: ...


class FederatedAuditSynchronizer:
    def __init__(self, audit_log, anchor: ExternalFederatedAuditAnchor, *, namespace: str):
        if not isinstance(namespace, str) or not namespace.strip() or len(namespace) > 256:
            raise ValueError("invalid_federated_audit_namespace")
        if not callable(getattr(audit_log, "checkpoint", None)):
            raise TypeError("verified_federated_audit_log_required")
        if not callable(getattr(audit_log, "checkpoint_at", None)):
            raise TypeError("historical_federated_audit_checkpoint_reader_required")
        if not callable(getattr(anchor, "read_checkpoint", None)):
            raise TypeError("external_federated_audit_anchor_required")
        self._audit_log = audit_log
        self._anchor = anchor
        self._namespace = namespace

    def synchronize(self) -> FederatedAuditCheckpoint:
        """Verify the anchored head or recover exactly one committed local append."""
        try:
            external = self._anchor.read_checkpoint(self._namespace)
        except Exception:
            raise PermissionError("external_federated_audit_anchor_unavailable") from None
        if not isinstance(external, FederatedAuditCheckpoint) or not external.is_well_formed():
            raise PermissionError("external_federated_audit_anchor_uninitialized_or_invalid")
        try:
            local = self._audit_log.checkpoint()
        except Exception:
            raise PermissionError("local_federated_audit_checkpoint_unavailable") from None
        if local == external:
            return local
        if local.sequence <= external.sequence:
            raise PermissionError("external_federated_audit_checkpoint_ahead_or_diverged")
        if local.sequence != external.sequence + 1:
            raise PermissionError("external_federated_audit_checkpoint_gap_exceeded")
        try:
            prefix = self._audit_log.checkpoint_at(external.sequence)
        except Exception:
            raise PermissionError("local_federated_audit_prefix_unavailable") from None
        if prefix != external:
            raise PermissionError("external_federated_audit_prefix_mismatch")
        try:
            advanced = self._anchor.compare_and_advance(
                self._namespace, external, local
            )
        except Exception:
            raise PermissionError("external_federated_audit_anchor_unavailable") from None
        if advanced is not True:
            raise PermissionError("external_federated_audit_anchor_conflict")
        return local
