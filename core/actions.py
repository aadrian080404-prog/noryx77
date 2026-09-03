from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import secrets
import threading
import time

from .contracts import ActionSpec, VerificationResult


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str
    verification: VerificationResult


@dataclass(frozen=True)
class AuthorizationGrant:
    """One-shot capability cryptographically bound to one exact action/execution."""
    action_id: str
    action_type: str
    target: str
    execution_id: str
    nonce: str
    expires_at: float
    signature: str


class AuthorizationAuthority:
    """Trusted issuer/verifier for short-lived, execution-bound action grants."""
    def __init__(self, secret: bytes, *, clock=time.monotonic, max_ttl: float = 300.0):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("authorization secret must be at least 32 bytes")
        if not callable(clock) or isinstance(max_ttl, bool) or not isinstance(max_ttl, (int, float)) or max_ttl <= 0:
            raise ValueError("invalid authorization configuration")
        self._secret = secret
        self._clock = clock
        self._max_ttl = float(max_ttl)
        self._used: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _payload(action: ActionSpec, execution_id: str, nonce: str, expires_at: float) -> bytes:
        fields = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "execution_id": execution_id,
            "nonce": nonce,
            "expires_at": expires_at,
        }
        return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _sign(self, action: ActionSpec, execution_id: str, nonce: str, expires_at: float) -> str:
        return hmac.new(self._secret, self._payload(action, execution_id, nonce, expires_at), hashlib.sha256).hexdigest()

    def issue(self, action: ActionSpec, execution_id: str, *, ttl: float = 60.0) -> AuthorizationGrant:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            raise ValueError("invalid action")
        if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id.encode("utf-8")) > 256:
            raise ValueError("invalid execution identity")
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl <= 0 or ttl > self._max_ttl:
            raise ValueError("invalid authorization ttl")
        nonce = secrets.token_urlsafe(32)
        expires_at = float(self._clock()) + float(ttl)
        return AuthorizationGrant(action.action_id, action.action_type, action.target, execution_id, nonce, expires_at, self._sign(action, execution_id, nonce, expires_at))

    def _verify_unconsumed(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant) -> bool:
        if not isinstance(grant, AuthorizationGrant) or not isinstance(execution_id, str) or not execution_id.strip():
            return False
        if grant.execution_id != execution_id or action.execution_id != execution_id:
            return False
        if (grant.action_id, grant.action_type, grant.target) != (action.action_id, action.action_type, action.target):
            return False
        if not grant.nonce or not isinstance(grant.signature, str):
            return False
        if not hmac.compare_digest(grant.signature, self._sign(action, execution_id, grant.nonce, grant.expires_at)):
            return False
        if self._clock() >= grant.expires_at:
            return False
        return True

    def verify(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant) -> bool:
        """Check grant authenticity/binding without consuming the one-shot capability."""
        if not self._verify_unconsumed(action, execution_id, grant):
            return False
        with self._lock:
            return grant.nonce not in self._used

    def consume(self, action: ActionSpec, execution_id: str, grant: AuthorizationGrant) -> bool:
        """Atomically consume a still-valid grant; safe under concurrent callers."""
        if not self._verify_unconsumed(action, execution_id, grant):
            return False
        with self._lock:
            if grant.nonce in self._used:
                return False
            self._used.add(grant.nonce)
            return True


class ActionGate:
    """Final fail-closed gate before an action can reach a tool/controller."""
    def __init__(self, policy, security, limits, authorization: AuthorizationAuthority | None = None):
        self.policy = policy
        self.security = security
        self.limits = limits
        self.authorization = authorization

    def authorize(self, action: ActionSpec, calls_used: int = 0, *, execution_id: str | None = None, grant: AuthorizationGrant | None = None) -> ActionDecision:
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
                if not self.authorization.verify(action, execution_id, grant):
                    return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant"))
            except Exception:
                return ActionDecision(False, "authorization verification failure", VerificationResult(False, "action_gate", "authorization_verification_failure"))
            # The grant satisfies only the explicit authorization predicate.
            # Keep the original immutable action for final atomic consumption.
            evaluation_action = replace(action, requires_authorization=False)

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

        # Consume only after every other gate passes. This prevents a denied
        # request from burning a valid capability, while the locked consume
        # remains the single atomic replay boundary immediately before allow.
        if authorization_pending:
            try:
                if not self.authorization.consume(action, execution_id, grant):
                    return ActionDecision(False, "invalid authorization grant", VerificationResult(False, "action_gate", "invalid_authorization_grant"))
            except Exception:
                return ActionDecision(False, "authorization verification failure", VerificationResult(False, "action_gate", "authorization_verification_failure"))
        return ActionDecision(True, "allowed", VerificationResult(True, "action_gate", "authorized"))
