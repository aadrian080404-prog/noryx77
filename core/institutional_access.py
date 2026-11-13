"""Deny-by-default institutional-access policy gate.

This module validates mandates and threshold approvals. It does not execute queries,
create zero-knowledge proofs, guarantee non-retention, or decide legal admissibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Callable


class AccessMode(str, Enum):
    PREDICATE = "predicate"
    MINIMIZED_DISCLOSURE = "minimized_disclosure"
    SUPERVISED_RECONSTRUCTION = "supervised_reconstruction"


@dataclass(frozen=True)
class InstitutionalMandate:
    mandate_id: str
    institution_id: str
    jurisdiction: str
    purpose: str
    permitted_scopes: tuple[str, ...]
    expires_at: float
    signature: bytes


@dataclass(frozen=True)
class InstitutionalApproval:
    approval_id: str
    approver_id: str
    request_digest: str
    expires_at: float
    signature: bytes


@dataclass(frozen=True)
class InstitutionalRequest:
    request_id: str
    institution_id: str
    jurisdiction: str
    purpose: str
    requested_scopes: tuple[str, ...]
    mode: AccessMode
    created_at: float


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str
    request_digest: str
    required_approvals: int


class InstitutionalAccessPolicy:
    """Policy-only gateway; signature verification is delegated to pinned trust roots."""

    def __init__(
        self,
        *,
        mandate_verifier: Callable[[InstitutionalMandate], bool],
        approval_verifier: Callable[[InstitutionalApproval], bool],
        approval_threshold: int = 2,
        supervisor_threshold: int = 1,
        max_request_age: float = 300.0,
    ) -> None:
        if not callable(mandate_verifier) or not callable(approval_verifier):
            raise ValueError("trusted_signature_verifiers_required")
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (approval_threshold, supervisor_threshold)):
            raise ValueError("invalid_approval_threshold")
        if approval_threshold < 2 or supervisor_threshold < 1:
            raise ValueError("threshold_below_safe_minimum")
        if isinstance(max_request_age, bool) or not isinstance(max_request_age, (int, float)) or not math.isfinite(float(max_request_age)) or max_request_age <= 0:
            raise ValueError("invalid_request_age")
        self._mandate_verifier = mandate_verifier
        self._approval_verifier = approval_verifier
        self.approval_threshold = approval_threshold
        self.supervisor_threshold = supervisor_threshold
        self.max_request_age = float(max_request_age)

    @staticmethod
    def digest(request: InstitutionalRequest) -> str:
        if not isinstance(request, InstitutionalRequest):
            raise TypeError("invalid_institutional_request")
        payload = {
            "request_id": request.request_id,
            "institution_id": request.institution_id,
            "jurisdiction": request.jurisdiction,
            "purpose": request.purpose,
            "requested_scopes": list(request.requested_scopes),
            "mode": request.mode.value if isinstance(request.mode, AccessMode) else str(request.mode),
            "created_at": request.created_at,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def evaluate(
        self,
        request: InstitutionalRequest,
        mandate: InstitutionalMandate,
        approvals: tuple[InstitutionalApproval, ...],
        *,
        now: float,
    ) -> AccessDecision:
        digest = ""
        required = self.approval_threshold
        try:
            digest = self.digest(request)
            if not isinstance(now, (int, float)) or isinstance(now, bool) or not math.isfinite(float(now)):
                return AccessDecision(False, "invalid_clock", digest, required)
            if not all(isinstance(x, str) and x.strip() for x in (
                request.request_id, request.institution_id, request.jurisdiction, request.purpose
            )):
                return AccessDecision(False, "invalid_request_fields", digest, required)
            if not isinstance(request.mode, AccessMode) or not request.requested_scopes:
                return AccessDecision(False, "invalid_request_scope_or_mode", digest, required)
            if len(set(request.requested_scopes)) != len(request.requested_scopes) or any(
                not isinstance(scope, str) or not scope.strip() for scope in request.requested_scopes
            ):
                return AccessDecision(False, "invalid_request_scopes", digest, required)
            if request.created_at > now or now - request.created_at > self.max_request_age:
                return AccessDecision(False, "request_expired_or_future", digest, required)
            if not isinstance(mandate, InstitutionalMandate):
                return AccessDecision(False, "mandate_required", digest, required)
            if (
                mandate.institution_id != request.institution_id
                or mandate.jurisdiction != request.jurisdiction
                or mandate.purpose != request.purpose
                or not set(request.requested_scopes).issubset(set(mandate.permitted_scopes))
                or not isinstance(mandate.expires_at, (int, float))
                or isinstance(mandate.expires_at, bool)
                or not math.isfinite(float(mandate.expires_at))
                or now >= mandate.expires_at
            ):
                return AccessDecision(False, "mandate_scope_or_validity_mismatch", digest, required)
            try:
                if not self._mandate_verifier(mandate):
                    return AccessDecision(False, "mandate_signature_invalid", digest, required)
            except Exception:
                return AccessDecision(False, "mandate_verifier_failed", digest, required)
            if request.mode is AccessMode.SUPERVISED_RECONSTRUCTION:
                required += self.supervisor_threshold
            if not isinstance(approvals, tuple) or len(approvals) < required:
                return AccessDecision(False, "approval_threshold_not_met", digest, required)
            approver_ids: set[str] = set()
            approval_ids: set[str] = set()
            for approval in approvals:
                if not isinstance(approval, InstitutionalApproval):
                    return AccessDecision(False, "invalid_approval", digest, required)
                if (
                    not approval.approver_id or not approval.approval_id
                    or approval.approver_id in approver_ids or approval.approval_id in approval_ids
                    or approval.request_digest != digest
                    or not isinstance(approval.expires_at, (int, float))
                    or isinstance(approval.expires_at, bool)
                    or not math.isfinite(float(approval.expires_at))
                    or now >= approval.expires_at
                ):
                    return AccessDecision(False, "approval_binding_or_expiry_invalid", digest, required)
                try:
                    if not self._approval_verifier(approval):
                        return AccessDecision(False, "approval_signature_invalid", digest, required)
                except Exception:
                    return AccessDecision(False, "approval_verifier_failed", digest, required)
                approver_ids.add(approval.approver_id)
                approval_ids.add(approval.approval_id)
            return AccessDecision(True, "policy_authorized_only_no_data_released", digest, required)
        except (TypeError, ValueError, AttributeError):
            return AccessDecision(False, "malformed_request", digest, required)
