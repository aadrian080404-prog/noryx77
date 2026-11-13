"""Policy-only institutional disclosure gate.

This module authorizes a narrowly scoped disclosure plan. It does not execute
queries, expose records, implement zero-knowledge proofs, or guarantee legal
non-retention. Signature verification and approver trust must be supplied by
separately managed cryptographic and identity infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Mapping, Protocol


class AccessMode(str, Enum):
    PREDICATE = "predicate"
    AGGREGATE = "aggregate"
    SUPERVISED = "supervised"


@dataclass(frozen=True)
class Mandate:
    mandate_id: str
    case_id: str
    jurisdiction: str
    purpose: str
    allowed_data_scopes: tuple[str, ...]
    valid_from: float
    expires_at: float
    issuer_id: str
    signature: bytes


@dataclass(frozen=True)
class AccessRequest:
    request_id: str
    mandate: Mandate
    jurisdiction: str
    purpose: str
    data_scopes: tuple[str, ...]
    mode: AccessMode
    created_at: float
    output_limit: int


@dataclass(frozen=True)
class Approval:
    approver_id: str
    request_digest: str
    role: str
    issued_at: float
    signature: bytes


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str
    request_digest: str
    mode: AccessMode | None
    approved_scopes: tuple[str, ...]
    approver_domains: tuple[str, ...]


class InstitutionalSignatureVerifier(Protocol):
    def verify_mandate(self, issuer_id: str, payload: bytes, signature: bytes) -> bool: ...
    def verify_approval(self, approver_id: str, payload: bytes, signature: bytes) -> bool: ...


class InstitutionalAccessGate:
    """Fail-closed M-of-N gate with mandate, purpose and scope binding.

    trusted_approvers maps immutable approver IDs to (independence_domain, role).
    It must come from a separately authenticated governance registry.
    """

    def __init__(
        self,
        *,
        verifier: InstitutionalSignatureVerifier,
        trusted_approvers: Mapping[str, tuple[str, str]],
        required_approvals: int = 2,
        required_roles: tuple[str, ...] = ("authorization", "oversight"),
        max_output_limit: int = 100,
        clock,
    ) -> None:
        if not callable(getattr(verifier, "verify_mandate", None)) or not callable(
            getattr(verifier, "verify_approval", None)
        ):
            raise TypeError("institutional_signature_verifier_required")
        if not isinstance(trusted_approvers, Mapping) or not trusted_approvers:
            raise ValueError("trusted_approver_registry_required")
        if isinstance(required_approvals, bool) or not isinstance(required_approvals, int) or required_approvals < 2:
            raise ValueError("at_least_two_approvals_required")
        if not isinstance(required_roles, tuple) or not required_roles or any(
            not isinstance(role, str) or not role.strip() for role in required_roles
        ):
            raise ValueError("invalid_required_roles")
        if isinstance(max_output_limit, bool) or not isinstance(max_output_limit, int) or max_output_limit < 1:
            raise ValueError("invalid_output_limit")
        if not callable(clock):
            raise TypeError("clock_must_be_callable")
        normalized: dict[str, tuple[str, str]] = {}
        for approver_id, metadata in trusted_approvers.items():
            if (
                not isinstance(approver_id, str) or not approver_id.strip()
                or not isinstance(metadata, tuple) or len(metadata) != 2
                or any(not isinstance(value, str) or not value.strip() for value in metadata)
            ):
                raise ValueError("invalid_trusted_approver")
            normalized[approver_id] = metadata
        self._verifier = verifier
        self._trusted_approvers = normalized
        self._required_approvals = required_approvals
        self._required_roles = frozenset(required_roles)
        self._max_output_limit = max_output_limit
        self._clock = clock

    @staticmethod
    def _canonical(value: object) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @classmethod
    def mandate_payload(cls, mandate: Mandate) -> bytes:
        return cls._canonical({
            "mandate_id": mandate.mandate_id,
            "case_id": mandate.case_id,
            "jurisdiction": mandate.jurisdiction,
            "purpose": mandate.purpose,
            "allowed_data_scopes": sorted(mandate.allowed_data_scopes),
            "valid_from": mandate.valid_from,
            "expires_at": mandate.expires_at,
            "issuer_id": mandate.issuer_id,
        })

    @classmethod
    def request_payload(cls, request: AccessRequest) -> bytes:
        mandate = request.mandate
        return cls._canonical({
            "request_id": request.request_id,
            "mandate_id": mandate.mandate_id,
            "case_id": mandate.case_id,
            "jurisdiction": request.jurisdiction,
            "purpose": request.purpose,
            "data_scopes": sorted(request.data_scopes),
            "mode": request.mode.value if isinstance(request.mode, AccessMode) else str(request.mode),
            "created_at": request.created_at,
            "output_limit": request.output_limit,
        })

    @classmethod
    def request_digest(cls, request: AccessRequest) -> str:
        return hashlib.sha256(cls.request_payload(request)).hexdigest()

    @staticmethod
    def _valid_text(value: object, limit: int = 256) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= limit

    @staticmethod
    def _valid_time(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

    def evaluate(self, request: AccessRequest, approvals: tuple[Approval, ...]) -> AccessDecision:
        digest = ""
        mode = request.mode if isinstance(request, AccessRequest) and isinstance(request.mode, AccessMode) else None
        if isinstance(request, AccessRequest):
            try:
                digest = self.request_digest(request)
            except (TypeError, ValueError, AttributeError):
                pass

        def deny(reason: str) -> AccessDecision:
            return AccessDecision(False, reason, digest, mode, (), ())

        if not isinstance(request, AccessRequest) or not isinstance(request.mandate, Mandate):
            return deny("invalid_request")
        mandate = request.mandate
        if mode is None:
            return deny("unsupported_access_mode")
        if not all(self._valid_text(value) for value in (
            request.request_id, request.jurisdiction, request.purpose,
            mandate.mandate_id, mandate.case_id, mandate.jurisdiction,
            mandate.purpose, mandate.issuer_id,
        )):
            return deny("invalid_request_fields")
        if not isinstance(request.data_scopes, tuple) or not request.data_scopes or any(
            not self._valid_text(scope) for scope in request.data_scopes
        ) or len(set(request.data_scopes)) != len(request.data_scopes):
            return deny("invalid_data_scopes")
        if not isinstance(mandate.allowed_data_scopes, tuple) or not mandate.allowed_data_scopes or any(
            not self._valid_text(scope) for scope in mandate.allowed_data_scopes
        ) or len(set(mandate.allowed_data_scopes)) != len(mandate.allowed_data_scopes):
            return deny("invalid_mandate_scopes")
        if not self._valid_time(request.created_at) or not self._valid_time(mandate.valid_from) or not self._valid_time(mandate.expires_at):
            return deny("invalid_time")
        now = self._clock()
        if not self._valid_time(now):
            return deny("invalid_clock")
        if mandate.valid_from >= mandate.expires_at or request.created_at < mandate.valid_from or request.created_at >= mandate.expires_at:
            return deny("mandate_not_valid_at_request_time")
        if now < mandate.valid_from or now >= mandate.expires_at:
            return deny("mandate_expired_or_not_yet_valid")
        if request.jurisdiction != mandate.jurisdiction:
            return deny("jurisdiction_mismatch")
        if request.purpose != mandate.purpose:
            return deny("purpose_mismatch")
        if not set(request.data_scopes).issubset(set(mandate.allowed_data_scopes)):
            return deny("scope_exceeds_mandate")
        if isinstance(request.output_limit, bool) or not isinstance(request.output_limit, int) or not 1 <= request.output_limit <= self._max_output_limit:
            return deny("output_limit_exceeded")
        if not isinstance(mandate.signature, bytes) or not mandate.signature:
            return deny("unsigned_mandate")
        try:
            if self._verifier.verify_mandate(mandate.issuer_id, self.mandate_payload(mandate), mandate.signature) is not True:
                return deny("invalid_mandate_signature")
        except Exception:
            return deny("mandate_verification_unavailable")

        if not isinstance(approvals, tuple) or len(approvals) < self._required_approvals:
            return deny("insufficient_approvals")
        seen_ids: set[str] = set()
        seen_domains: set[str] = set()
        seen_roles: set[str] = set()
        for approval in approvals:
            if not isinstance(approval, Approval):
                return deny("invalid_approval")
            if (
                not self._valid_text(approval.approver_id)
                or not self._valid_text(approval.role)
                or not self._valid_time(approval.issued_at)
                or not isinstance(approval.signature, bytes) or not approval.signature
                or approval.request_digest != digest
            ):
                return deny("approval_binding_invalid")
            trusted = self._trusted_approvers.get(approval.approver_id)
            if trusted is None:
                return deny("untrusted_approver")
            domain, trusted_role = trusted
            if approval.role != trusted_role or approval.role not in self._required_roles:
                return deny("approver_role_mismatch")
            if approval.approver_id in seen_ids or domain in seen_domains or approval.role in seen_roles:
                return deny("approver_independence_violation")
            if approval.issued_at > now or approval.issued_at < request.created_at or approval.issued_at >= mandate.expires_at:
                return deny("approval_outside_validity_window")
            payload = self._canonical({
                "approver_id": approval.approver_id,
                "request_digest": digest,
                "role": approval.role,
                "issued_at": approval.issued_at,
            })
            try:
                if self._verifier.verify_approval(approval.approver_id, payload, approval.signature) is not True:
                    return deny("invalid_approval_signature")
            except Exception:
                return deny("approval_verification_unavailable")
            seen_ids.add(approval.approver_id)
            seen_domains.add(domain)
            seen_roles.add(approval.role)
        if not self._required_roles.issubset(seen_roles) or len(seen_ids) < self._required_approvals:
            return deny("independent_approval_quorum_not_met")
        return AccessDecision(True, "authorized_plan_only", digest, mode, tuple(sorted(request.data_scopes)), tuple(sorted(seen_domains)))
