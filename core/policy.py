from .contracts import ActionSpec


class PolicyEngine:
    """Central authorization boundary; malformed or unknown actions are denied by default."""

    ALLOWED_ACTIONS = {
        "observe", "search", "navigate", "compute", "create", "transform", "store",
        "jarvis_capability",
    }
    HIGH_RISK = {"execute_external", "publish", "financial", "delete_external", "system_change"}

    def evaluate(self, action: ActionSpec) -> dict:
        if not isinstance(action, ActionSpec) or not action.is_well_formed():
            return {"allowed": False, "reason": "invalid_action"}
        if action.action_type in self.HIGH_RISK:
            return {"allowed": False, "reason": "authorization_required"}
        if action.action_type not in self.ALLOWED_ACTIONS:
            return {"allowed": False, "reason": "unsupported_action"}
        if action.requires_authorization:
            return {"allowed": False, "reason": "authorization_required"}
        return {"allowed": True, "reason": "policy_ok"}

    def allows(self, action: ActionSpec) -> bool:
        return bool(self.evaluate(action).get("allowed"))
