"""Final federated action boundary requiring both principal and agent grants.

Envelope capability claims are treated as request constraints, never as local
permissions. Local policy and security still decide whether the ActionSpec is
allowed. The executor must be a bounded local dispatch/enqueue callback: both
identity registries remain locked through one-shot consumption and dispatch so
revocation cannot race the final boundary.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .actions import ActionDecision, ActionGate, AuthorizationGrant
from .contracts import ActionSpec
from .federation_admission import FederatedAdmission
from .identity import AgentIdentity
from .principal_authorization import (
    PrincipalAuthorizationAuthority,
    PrincipalAuthorizationGrant,
)


class FederatedActionGate:
    """Compose local ActionGate, agent grant and durable principal grant."""

    def __init__(
        self,
        action_gate: ActionGate,
        principal_authority: PrincipalAuthorizationAuthority,
        *,
        local_policy_version: str,
    ) -> None:
        if not isinstance(action_gate, ActionGate):
            raise TypeError("action_gate_required")
        if not callable(getattr(principal_authority, "consume_and_execute", None)):
            raise TypeError("principal_authority_required")
        if not callable(getattr(action_gate.authorization, "consume_and_execute", None)):
            raise TypeError("agent_authorization_authority_required")
        if not isinstance(local_policy_version, str) or not local_policy_version.strip():
            raise ValueError("local_policy_version_required")
        self._gate = action_gate
        self._principals = principal_authority
        self._agents = action_gate.authorization
        self._policy_version = local_policy_version

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
        """Authorize a single action and invoke a bounded local dispatcher.

        Lock order is always agent registry -> principal registry. Do not call
        this from a callback that already holds either registry in reverse order.
        The dispatcher must not perform network I/O or mutate either trust store;
        enqueue work locally and return. External work belongs after this gate.
        """
        if not isinstance(admission, FederatedAdmission):
            return self._denied("invalid_federated_admission"), None
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

        # First run the existing ActionGate's local budget, policy and security
        # checks without consuming either grant. The two grants are consumed only
        # in the final nested critical section below.
        local_action = replace(action, requires_authorization=False)
        decision = self._gate.authorize(
            local_action, calls_used, execution_id=admission.execution_id
        )
        if not decision.allowed:
            return decision, None

        def consume_principal_and_dispatch() -> object | None:
            consumed, result = self._principals.consume_and_execute(
                action, admission.execution_id, principal_grant, executor
            )
            if not consumed:
                raise PermissionError("principal_grant_rejected")
            return result

        try:
            agent_consumed, result = self._agents.consume_and_execute(
                action, admission.execution_id, agent_grant,
                agent_identity, consume_principal_and_dispatch,
            )
        except Exception:
            return self._denied("federated_dispatch_failed"), None
        if not agent_consumed:
            return self._denied("agent_grant_rejected"), None
        return decision, result
