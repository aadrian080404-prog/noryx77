"""Structured, secret-minimizing audit records for federated action decisions.

The recorder writes to the existing in-process AuditLog. It does not provide
durable storage, external anchoring, or automatic gate integration.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Callable

from .actions import ActionDecision
from .audit import AuditLog
from .contracts import ActionSpec
from .federation_admission import FederatedAdmission


_MAX_FINGERPRINT_BYTES = 65536


class FederatedActionAuditRecorder:
    """Record verified federated decisions without persisting raw action inputs."""

    def __init__(
        self,
        audit_log: AuditLog,
        *,
        clock: Callable[[], int | float] = time.time,
    ) -> None:
        if not callable(getattr(audit_log, "record", None)):
            raise TypeError("audit_log_required")
        if not callable(clock):
            raise TypeError("audit_clock_required")
        self._audit = audit_log
        self._clock = clock

    @staticmethod
    def _action_fingerprint(action: ActionSpec) -> str:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("valid_action_required")
        payload = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "risk_class": action.risk_class,
            "execution_id": action.execution_id,
            "parameters": action.parameters,
        }
        try:
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError):
            raise ValueError("action_parameters_not_canonicalizable") from None
        if len(encoded) > _MAX_FINGERPRINT_BYTES:
            raise ValueError("action_fingerprint_payload_too_large")
        return hashlib.sha256(encoded).hexdigest()

    def record_decision(
        self,
        admission: FederatedAdmission,
        action: ActionSpec,
        decision: ActionDecision,
    ) -> dict:
        if not isinstance(admission, FederatedAdmission) or not admission.is_verified():
            raise ValueError("verified_federated_admission_required")
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("valid_action_required")
        if not isinstance(decision, ActionDecision) or not isinstance(decision.allowed, bool):
            raise ValueError("valid_action_decision_required")
        if not isinstance(decision.reason, str) or not decision.reason.strip():
            raise ValueError("action_decision_reason_required")
        try:
            timestamp = self._clock()
        except Exception:
            raise RuntimeError("audit_clock_unavailable") from None
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or timestamp < 0:
            raise RuntimeError("audit_clock_invalid")
        try:
            finite_timestamp = math.isfinite(float(timestamp))
        except (OverflowError, ValueError):
            finite_timestamp = False
        if not finite_timestamp:
            raise RuntimeError("audit_clock_invalid")
        return self._audit.record(
            "federated_action_decision",
            principal_id=admission.principal_id,
            agent_id=admission.agent_id,
            execution_id=admission.execution_id,
            issuer_key_id=admission.issuer_key_id,
            policy_version=admission.policy_version,
            state_version=admission.state_version,
            action_id=action.action_id,
            action_type=action.action_type,
            action_fingerprint=self._action_fingerprint(action),
            allowed=decision.allowed,
            reason=decision.reason,
            timestamp=timestamp,
        )


    def record_outcome(
        self,
        admission: FederatedAdmission,
        action: ActionSpec,
        *,
        outcome: str,
        reason: str = "",
    ) -> dict:
        """Record the final local dispatch outcome without storing its result."""
        allowed_outcomes = {
            "dispatched",
            "executor_failed",
            "agent_grant_rejected",
            "principal_grant_rejected",
            "principal_agent_binding_rejected",
            "dispatch_failed",
        }
        if not isinstance(admission, FederatedAdmission) or not admission.is_verified():
            raise ValueError("verified_federated_admission_required")
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("valid_action_required")
        if outcome not in allowed_outcomes:
            raise ValueError("invalid_federated_dispatch_outcome")
        if not isinstance(reason, str) or len(reason) > 128:
            raise ValueError("invalid_federated_dispatch_reason")
        try:
            timestamp = self._clock()
        except Exception:
            raise RuntimeError("audit_clock_unavailable") from None
        if (isinstance(timestamp, bool) or not isinstance(timestamp, (int, float))
                or not math.isfinite(float(timestamp)) or timestamp < 0):
            raise RuntimeError("audit_clock_invalid")
        return self._audit.record(
            "federated_action_outcome",
            principal_id=admission.principal_id,
            agent_id=admission.agent_id,
            execution_id=admission.execution_id,
            issuer_key_id=admission.issuer_key_id,
            policy_version=admission.policy_version,
            action_id=action.action_id,
            action_type=action.action_type,
            action_fingerprint=self._action_fingerprint(action),
            outcome=outcome,
            reason=reason,
            timestamp=timestamp,
        )
