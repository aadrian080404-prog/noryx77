"""Final federated action boundary requiring principal, agent and audit controls.

Envelope capability claims are request constraints, never local permissions.
Local policy and security decide whether the ActionSpec is allowed. When
authorization is allowed, a verified audit record must be committed before
one-shot grants are consumed or the local dispatcher is invoked.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .actions import ActionDecision, ActionGate, AuthorizationGrant
from .contracts import ActionSpec
from .federation_admission import FederatedAdmission
from .federated_action_audit import FederatedActionAuditRecorder
from .identity import AgentIdentity
from .sqlite_principal_agent_binding import PrincipalAgentBindingRejected
from .principal_authorization import (
    PrincipalAuthorizationAuthority,
    PrincipalAuthorizationGrant,
)


class FederatedActionGate:
    """Compose local ActionGate, agent grant, principal grant and audit."""

    def __init__(
        self,
        action_gate: ActionGate,
        principal_authority: PrincipalAuthorizationAuthority,
        binding_registry: object,
        *,
        local_policy_version: str,
        audit_recorder: FederatedActionAuditRecorder,
    ) -> None:
        if not isinstance(action_gate, ActionGate):
            raise TypeError("action_gate_required")
        if not callable(getattr(principal_authority, "consume_and_execute", None)):
            raise TypeError("principal_authority_required")
        if not callable(getattr(binding_registry, "with_active_binding", None)):
            raise TypeError("principal_agent_binding_registry_required")
        if not callable(getattr(action_gate.authorization, "consume_and_execute", None)):
            raise TypeError("agent_authorization_authority_required")
        if not isinstance(local_policy_version, str) or not local_policy_version.strip():
            raise ValueError("local_policy_version_required")
        if not isinstance(audit_recorder, FederatedActionAuditRecorder):
            raise TypeError("federated_audit_recorder_required")
        self._gate = action_gate
        self._principals = principal_authority
        self._bindings = binding_registry
        self._agents = action_gate.authorization
        self._policy_version = local_policy_version
        self._audit = audit_recorder

    @staticmethod
    def _denied(reason: str) -> ActionDecision:
        from .contracts import VerificationResult
        return ActionDecision(
            False, reason, VerificationResult(False, "federated_action_gate", reason)
        )

    def authorize_and_dispatch(
        self,
        admission: FederatedAdmission,
        action: ActionSpec,
        *,
        agent_identity: AgentIdentity,
        agent_grant: AuthorizationGrant,
        principal_grant: PrincipalAuthorizationGrant,
        required_capability: str,
        executor: Callable[[], object],
        calls_used: int = 0,
    ) -> tuple[ActionDecision, object | None]:
        """Authorize one action and call a bounded local dispatcher.

        Lock order is agent registry -> principal registry -> binding SQLite.
        The live principal-agent binding remains locked through grant consumption
        and bounded local dispatch. The dispatcher must not perform network I/O
        or mutate trust stores; enqueue locally and return.
        The audit decision is durably appended to the configured AuditLog before
        grant consumption. Audit failure is fail-closed and prevents dispatch.
        """
        if not isinstance(admission, FederatedAdmission):
            return self._denied("invalid_federated_admission"), None
        if not admission.is_verified():
            return self._denied("unverified_or_modified_federated_admission"), None
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return self._denied("invalid_action"), None
        if not isinstance(agent_identity, AgentIdentity) or not agent_identity.is_well_formed():
            return self._denied("invalid_agent_identity"), None
        if not isinstance(agent_grant, AuthorizationGrant):
            return self._denied("agent_grant_required"), None
        if not isinstance(principal_grant, PrincipalAuthorizationGrant):
            return self._denied("principal_grant_required"), None
        if not callable(executor):
            return self._denied("dispatcher_required"), None
        if admission.policy_version != self._policy_version:
            return self._denied("federated_policy_version_mismatch"), None
        if (
            not isinstance(required_capability, str)
            or not required_capability.strip()
            or required_capability != action.action_type
            or required_capability not in admission.asserted_capabilities
        ):
            return self._denied("federated_capability_mismatch"), None
        if (
            admission.execution_id != action.execution_id
            or admission.agent_id != agent_identity.agent_id
            or admission.principal_id != principal_grant.principal_id
            or agent_grant.principal_id != agent_identity.agent_id
        ):
            return self._denied("federated_identity_or_execution_mismatch"), None
        if not action.requires_authorization:
            return self._denied("explicit_authorization_required"), None

        # Local policy/budget/security checks run before either one-shot grant.
        local_action = replace(action, requires_authorization=False)
        decision = self._gate.authorize(
            local_action, calls_used, execution_id=admission.execution_id
        )
        try:
            self._audit.record_decision(admission, action, decision)
        except Exception:
            # No grant has been consumed and the executor has not been called.
            return self._denied("federated_audit_unavailable"), None
        if not decision.allowed:
            return decision, None

        dispatch_state = {
            "executor_started": False,
            "executor_failed": False,
            "principal_grant_attempted": False,
        }

        def audited_executor() -> object:
            dispatch_state["executor_started"] = True
            try:
                return executor()
            except Exception:
                dispatch_state["executor_failed"] = True
                raise

        def record_outcome(outcome: str, reason: str = "") -> bool:
            try:
                self._audit.record_outcome(
                    admission, action, outcome=outcome, reason=reason
                )
                return True
            except Exception:
                return False

        def consume_principal_and_dispatch() -> object | None:
            dispatch_state["principal_grant_attempted"] = True
            consumed, result = self._principals.consume_and_execute(
                action, admission.execution_id, principal_grant, audited_executor
            )
            if not consumed:
                raise PermissionError("principal_grant_rejected")
            return result

        try:
            agent_consumed, result = self._bindings.with_active_binding(
                principal_grant.principal_id,
                agent_identity.agent_id,
                lambda: self._agents.consume_and_execute(
                    action, admission.execution_id, agent_grant,
                    agent_identity, consume_principal_and_dispatch,
                ),
            )
        except PrincipalAgentBindingRejected:
            if not record_outcome(
                "principal_agent_binding_rejected",
                "principal_agent_binding_not_active",
            ):
                return self._denied("federated_outcome_audit_unavailable"), None
            return self._denied("principal_agent_binding_not_active"), None
        except Exception:
            if dispatch_state["executor_started"]:
                outcome = (
                    "executor_failed"
                    if dispatch_state["executor_failed"] else "dispatch_failed"
                )
            elif dispatch_state["principal_grant_attempted"]:
                outcome = "principal_grant_rejected"
            else:
                outcome = "dispatch_failed"
            if not record_outcome(outcome, "federated_dispatch_exception"):
                return self._denied("federated_outcome_audit_unavailable"), None
            return self._denied("federated_dispatch_failed"), None

        if not agent_consumed:
            if dispatch_state["executor_started"]:
                outcome = (
                    "executor_failed"
                    if dispatch_state["executor_failed"] else "dispatch_failed"
                )
            elif dispatch_state["principal_grant_attempted"]:
                outcome = "principal_grant_rejected"
            else:
                outcome = "agent_grant_rejected"
            if not record_outcome(outcome, outcome):
                return self._denied("federated_outcome_audit_unavailable"), None
            return self._denied(
                "federated_dispatch_failed"
                if dispatch_state["executor_started"] else outcome
            ), None

        if not record_outcome("dispatched"):
            # The local dispatcher may already have enqueued work. Do not claim
            # it was rolled back; surface that its final audit receipt is missing.
            return self._denied("federated_outcome_audit_unavailable_after_dispatch"), None
        return decision, result
