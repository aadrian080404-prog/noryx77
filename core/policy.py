from .contracts import ActionSpec


class PolicyEngine:
    """Central authorization boundary; malformed or unknown actions are denied by default."""

    ALLOWED_ACTIONS = {
        "observe", "search", "navigate", "compute", "create", "transform", "store",
        "jarvis_capability", "agent_collaboration", "web_research", "chess_analyze",
        "payments", "flights", "insurance", "execute_external", "publish",
        "financial", "delete_external", "system_change",
    }
    # These action types can cause financial, external, destructive, or durable
    # side effects. Their presence in ALLOWED_ACTIONS is not sufficient to run:
    # ActionGate must verify a one-shot grant before passing authorization_verified.
    REQUIRES_AUTHORIZATION = frozenset({
        "payments", "flights", "insurance", "execute_external", "publish",
        "financial", "delete_external", "system_change",
    })
    HIGH_RISK = REQUIRES_AUTHORIZATION

    def evaluate(self, action: ActionSpec, *, authorization_verified: bool = False) -> dict:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return {"allowed": False, "reason": "invalid_action"}
        if not isinstance(authorization_verified, bool):
            return {"allowed": False, "reason": "invalid_authorization_state"}
        if action.action_type not in self.ALLOWED_ACTIONS:
            return {"allowed": False, "reason": "unsupported_action"}
        if action.action_type in self.REQUIRES_AUTHORIZATION:
            if not authorization_verified:
                return {"allowed": False, "reason": "authorization_required"}
            if action.risk_class != "high":
                return {"allowed": False, "reason": "high_risk_class_required"}
        if action.risk_class == "high" and not authorization_verified:
            return {"allowed": False, "reason": "authorization_required"}
        if action.requires_authorization and not authorization_verified:
            return {"allowed": False, "reason": "authorization_required"}
        return {"allowed": True, "reason": "policy_ok"}

    def allows(self, action: ActionSpec, *, authorization_verified: bool = False) -> bool:
        return bool(self.evaluate(action, authorization_verified=authorization_verified).get("allowed"))
