"""ExecutionFabric decorator that records privacy-minimized audit evidence."""
from __future__ import annotations

import hashlib
import json

from .audit import AuditLog
from .execution_fabric import ExecutionFabric, ProposedAction

MAX_AUDIT_ACTION_BYTES = 64 * 1024


class AuditedExecutionFabric:
    """Record action intent and outcome around the deny-by-default execution fabric.

    Only a digest of canonical action parameters is recorded; parameter values,
    credentials and process output are never copied into the audit event.
    """

    def __init__(self, fabric: ExecutionFabric, audit: AuditLog) -> None:
        if not isinstance(fabric, ExecutionFabric):
            raise TypeError("execution_fabric_required")
        if not isinstance(audit, AuditLog):
            raise TypeError("audit_log_required")
        self._fabric = fabric
        self._audit = audit

    def execute(self, action: ProposedAction):
        if not isinstance(action, ProposedAction):
            raise TypeError("proposed_action_required")
        try:
            canonical = json.dumps(
                dict(action.parameters),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("execution_parameters_not_auditable") from exc
        if len(canonical) > MAX_AUDIT_ACTION_BYTES:
            raise ValueError("execution_audit_payload_too_large")
        digest = hashlib.sha256(canonical).hexdigest()
        metadata = {
            "action_id": action.action_id,
            "environment": action.environment,
            "action_type": action.action_type,
            "target": action.target,
            "parameters_sha256": digest,
        }

        # If intent cannot be recorded, the protected action is never invoked.
        self._audit.record("execution.requested", **metadata)
        try:
            result = self._fabric.execute(action)
        except Exception as exc:
            self._audit.record(
                "execution.failed",
                action_id=action.action_id,
                error_type=type(exc).__name__,
            )
            raise

        # If this append fails, the preceding intent record remains as evidence
        # that an action was started; callers must treat the outcome as unknown.
        try:
            self._audit.record(
                "execution.completed",
                action_id=action.action_id,
                result_type=type(result).__name__,
            )
        except Exception as exc:
            raise RuntimeError("execution_completed_but_audit_commit_failed") from exc
        return result

    def environments(self) -> tuple[str, ...]:
        return self._fabric.environments()
