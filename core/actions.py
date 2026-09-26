from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import math
import secrets
import threading
import time
from collections.abc import Mapping

from .contracts import ActionSpec, VerificationResult
from .identity import AgentIdentity, IdentityRegistry


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str
    verification: VerificationResult


@dataclass(frozen=True)
class AuthorizationGrant:
    """One-shot capability bound to one exact action, execution and principal key."""
    action_id: str
    action_type: str
    target: str
    execution_id: str
    principal_id: str
    principal_key_fingerprint: str
    nonce: str
    expires_at: float
    signature: str


class AuthorizationAuthority:
    """Trusted issuer/verifier for short-lived, execution- and identity-bound grants."""
    def __init__(
        self,
        secret: bytes,
        *,
        clock=time.monotonic,
        max_ttl: float = 300.0,
        identity_registry: IdentityRegistry | None = None,
    ):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("authorization secret must be at least 32 bytes")
        if not callable(clock) or isinstance(max_ttl, bool) or not isinstance(max_ttl, (int, float)) or not math.isfinite(float(max_ttl)) or max_ttl <= 0:
            raise ValueError("invalid authorization configuration")
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise ValueError("invalid identity registry")
        self._secret = bytes(secret)
        self._clock = clock
        self._max_ttl = float(max_ttl)
        self._identity_registry = identity_registry
        self._used: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _fingerprint(identity: AgentIdentity) -> str:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        return hashlib.sha256(identity.public_key).hexdigest()

    @staticmethod
    def _canonicalize(value):
        """Return a deterministic JSON-safe representation or fail closed."""
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("non_finite_action_parameter")
            return value
        if isinstance(value, Mapping):
            items = []
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError("non_string_action_parameter_key")
                items.append((key, AuthorizationAuthority._canonicalize(item)))
            items.sort(key=lambda pair: pair[0])
            return {key: item for key, item in items}
        if isinstance(value, (list, tuple)):
            return [AuthorizationAuthority._canonicalize(item) for item in value]
        raise ValueError("unsupported_action_parameter_type")

    @classmethod
    def _action_fingerprint(cls, action: ActionSpec) -> str:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("invalid action")
        canonical = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "parameters": cls._canonicalize(action.parameters),
            "risk_class": action.risk_class,
            "requires_authorization": action.requires_authorization,
            "execution_id": action.execution_id,
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _payload(cls, action: ActionSpec, execution_id: str, principal_id: str, principal_key_fingerprint: str, nonce: str, expires_at: float) -> bytes:
        fields = {
            "action_fingerprint": cls._action_fingerprint(action),
            "execution_id": execution_id,
            "principal_id": principal_id,
            "principal_key_fingerprint": principal_key_fingerprint,
            "nonce": nonce,
            "expires_at": expires_at,
        }
        return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _sign(self, action: ActionSpec, execution_id: str, principal_id: str, principal_key_fingerprint: str, nonce: str, expires_at: float) -> str:
        return hmac.new(self._secret, self._payload(action, execution_id, principal_id, principal_key_fingerprint, nonce, expires_at), hashlib.sha256).hexdigest()

    def issue(self, action: ActionSpec, execution_id: str, *, principal: AgentIdentity | None = None, ttl: float = 60.0) -> AuthorizationGrant:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("invalid action")
        if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id.encode("utf-8")) > 256:
            raise ValueError("invalid execution identity")
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or not math.isfinite(float(ttl)) or ttl <= 0 or ttl > self._max_ttl:
            raise ValueError("invalid authorization ttl")
        if action.execution_id != execution_id:
            raise ValueError("execution identity mismatch")
        # Compute before issuing so unsupported/non-canonical parameters cannot receive a capability.
        self._action_fingerprint(action)
        if self._identity_registry is not None:
            if not isinstance(principal, AgentIdentity) or not self._identity_registry.is_trusted(principal):
                raise ValueError("untrusted_authorization_principal")
        elif principal is not None and not isinstance(principal, AgentIdentity):
            raise ValueError("invalid_authorization_principal")
        principal_id = principal.agent_id if principal is not None else ""
        fingerprint = self._fingerprint(principal) if principal is not None else ""
        nonce = secrets.token_urlsafe(32)
        expires_at = float(self._clock()) + float(ttl)
        signature = self._sign(action, execution_id, principal_id, fingerprint, nonce, expires_at)
        return AuthorizationGrant(action.action_id, action.action_type, action.target, execution_id, principal_id, fingerprint, nonce, expires_at, signature)

    def _verify_unconsumed(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant, principal: AgentIdentity | None = None) -> bool:
        if not isinstance(grant, AuthorizationGrant) or not isinstance(execution_id, str) or not execution_id.strip():
            return False
        try:
            action_fingerprint = self._action_fingerprint(action)
        except (TypeError, ValueError, OverflowError):
            return False
        if grant.execution_id != execution_id or action.execution_id != execution_id:
            return False
        if not grant.nonce or not isinstance(grant.signature, str):
            return False
        if self._identity_registry is not None:
            if not isinstance(principal, AgentIdentity) or not self._identity_registry.is_trusted(principal):
                return False
        if principal is not None:
            if not isinstance(principal, AgentIdentity) or not principal.is_well_formed():
                return False
            if grant.principal_id != principal.agent_id:
                return False
            if not hmac.compare_digest(grant.principal_key_fingerprint, self._fingerprint(principal)):
                return False
        elif grant.principal_id or grant.principal_key_fingerprint:
            return False
        expected = hmac.new(
            self._secret,
            json.dumps(
                {
                    "action_fingerprint": action_fingerprint,
                    "execution_id": execution_id,
                    "principal_id": grant.principal_id,
                    "principal_key_fingerprint": grant.principal_key_fingerprint,
                    "nonce": grant.nonce,
                    "expires_at": grant.expires_at,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(grant.signature, expected):
            return False
        if not isinstance(grant.expires_at, (int, float)) or isinstance(grant.expires_at, bool) or not math.isfinite(float(grant.expires_at)):
            return False
        if self._clock() >= grant.expires_at:
            return False
        return True

    def verify(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant, *, principal: AgentIdentity | None = None) -> bool:
        """Check authenticity, current trust and binding without consuming the grant."""
        if not self._verify_unconsumed(action, execution_id, grant, principal):
            return False
        with self._lock:
            return grant.nonce not in self._used

    def consume(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant, *, principal: AgentIdentity | None = None) -> bool:
        """Atomically consume a still-valid, currently trusted grant."""
        if not self._verify_unconsumed(action, execution_id, grant, principal):
            return False
        with self._lock:
            if grant.nonce in self._used:
                return False
            if self._identity_registry is not None:
                if not isinstance(principal, AgentIdentity) or not self._identity_registry.is_trusted(principal):
                    return False
            self._used.add(grant.nonce)
            return True

    def consume_and_execute(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant, principal: AgentIdentity, executor) -> tuple[bool, object | None]:
        """Linearize grant consumption and dispatch against identity revocation."""
        if not callable(executor) or self._identity_registry is None:
            return False, None
        if not self._verify_unconsumed(action, execution_id, grant, principal):
            return False, None
        with self._lock:
            if grant.nonce in self._used:
                return False, None
            with self._identity_registry._lock:
                if not self._identity_registry.is_trusted(principal):
                    return False, None
                self._used.add(grant.nonce)
                # The capability is consumed before dispatch; executor failure is an execution
                # failure, never an authorization success and never a reason to restore the grant.
                return True, executor()


class ActionGate:
    """Final fail-closed gate before an action can reach a tool/controller."""
    def __init__(self, policy, security, limits, authorization: AuthorizationAuthority | None = None):
        self.policy = policy
        self.security = security
        self.limits = limits
        self.authorization = authorization

    def authorize(self, action: ActionSpec, calls_used: int = 0, *, execution_id: str | None = None, grant: AuthorizationGrant | None = None, principal: AgentIdentity | None = None) -> ActionDecision:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return ActionDecision(False, "invalid action contract", VerificationResult(False, "action_gate", "invalid_action_contract"))
        if isinstance(calls_used, bool) or not isinstance(calls_used, int) or calls_used < 0:
            return ActionDecision(False, "invalid call count", VerificationResult(False, "action_gate", "invalid_call_count"))
        if execution_id is not None:
            if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id.encode("utf-8")) > 256:
                return ActionDecision(False, "invalid execution identity", VerificationResult(False, "action_gate", "invalid_execution_identity"))
            if action.execution_id != execution_id:
                return ActionDecision(False, "execution identity mismatch", VerificationResult(False, "action_gate", "execution_identity_mismatch"))
        elif action.execution_id:
            return ActionDecision(False, "execution identity required", VerificationResult(False, "action_gate", "execution_identity_required"))
        if self.limits.max_actions_per_task - calls_used <= 0:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget"))
        evaluation_action = action
        authorization_pending = action.requires_authorization
        if authorization_pending:
            if self.authorization is None or execution_id is None or grant is None:
                return ActionDecision(False, "authorization required", VerificationResult(False, "action_gate", "authorization_required"))
            try:
                if not self.authorization.verify(action, execution_id, grant, principal=principal):
                    return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant"))
            except Exception:
                return ActionDecision(False, "authorization verification failure", VerificationResult(False, "action_gate", "authorization_verification_failure"))
            evaluation_action = replace(
                action,
                requires_authorization=False,
                risk_class="sensitive" if action.risk_class == "high" else action.risk_class,
            )
        try:
            policy_allowed = self.policy.allows(evaluation_action)
        except Exception:
            return ActionDecision(False, "policy evaluation failure", VerificationResult(False, "action_gate", "policy_evaluation_failure"))
        if not policy_allowed:
            return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy"))
        try:
            security_allowed = self.security.allows(evaluation_action)
        except Exception:
            return ActionDecision(False, "security evaluation failure", VerificationResult(False, "action_gate", "security_evaluation_failure"))
        if not security_allowed:
            return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security"))
        if authorization_pending:
            try:
                if not self.authorization.consume(action, execution_id, grant, principal=principal):
                    return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant"))
            except Exception:
                return ActionDecision(False, "authorization verification failure", VerificationResult(False, "action_gate", "authorization_verification_failure"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))

    def authorize_and_execute(self, action: ActionSpec, executor, calls_used: int = 0, *, execution_id: str | None = None, grant: AuthorizationGrant | None = None, principal: AgentIdentity | None = None) -> tuple[ActionDecision, object | None]:
        """Gate and dispatch an action, atomically for identity-bound authorized actions."""
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return self.authorize(action, calls_used, execution_id=execution_id, grant=grant, principal=principal), None
        if not callable(executor):
            return ActionDecision(False, "invalid executor", VerificationResult(False, "action_gate", "invalid_executor")), None
        if isinstance(calls_used, bool) or not isinstance(calls_used, int) or calls_used < 0:
            return ActionDecision(False, "invalid call count", VerificationResult(False, "action_gate", "invalid_call_count")), None
        if self.limits.max_actions_per_task - calls_used <= 0:
            return ActionDecision(False, "action budget exceeded", VerificationResult(False, "action_gate", "budget")), None
        if execution_id is not None:
            if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id.encode("utf-8")) > 256:
                return ActionDecision(False, "invalid execution identity", VerificationResult(False, "action_gate", "invalid_execution_identity")), None
            if action.execution_id != execution_id:
                return ActionDecision(False, "execution identity mismatch", VerificationResult(False, "action_gate", "execution_identity_mismatch")), None
        elif action.execution_id:
            return ActionDecision(False, "execution identity required", VerificationResult(False, "action_gate", "execution_identity_required")), None

        if not action.requires_authorization:
            decision = self.authorize(action, calls_used, execution_id=execution_id, grant=grant, principal=principal)
            if not decision.allowed:
                return decision, None
            try:
                return decision, executor()
            except Exception:
                return ActionDecision(False, "execution failure", VerificationResult(False, "action_gate", "execution_failure")), None

        if self.authorization is None or execution_id is None or grant is None or principal is None:
            return self.authorize(action, calls_used, execution_id=execution_id, grant=grant, principal=principal), None

        evaluation_action = replace(action, requires_authorization=False)
        try:
            if not self.authorization.verify(action, execution_id, grant, principal=principal):
                return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant")), None
            if not self.policy.allows(evaluation_action):
                return ActionDecision(False, "policy denied", VerificationResult(False, "action_gate", "policy")), None
            if not self.security.allows(evaluation_action):
                return ActionDecision(False, "security boundary denied", VerificationResult(False, "action_gate", "security")), None
        except Exception:
            return ActionDecision(False, "authorization verification failure", VerificationResult(False, "action_gate", "authorization_verification_failure")), None

        try:
            consumed, result = self.authorization.consume_and_execute(action, execution_id, grant, principal, executor)
        except Exception:
            return ActionDecision(False, "execution failure", VerificationResult(False, "action_gate", "execution_failure")), None
        if not consumed:
            return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant")), None
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized")), result
