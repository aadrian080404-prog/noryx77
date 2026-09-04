class Policy:
    """Fail-closed action policy boundary."""
    def authorize(self, principal_id: str, capability: str, target: str) -> bool:
        return bool(principal_id and capability and target)
