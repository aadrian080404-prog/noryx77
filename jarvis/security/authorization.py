class Authorization:
    """Deny by default; explicit grants bind principal to capability and target."""
    def __init__(self): self._grants = set()
    def grant(self, principal_id: str, capability: str, target: str):
        if not all(isinstance(x, str) and x.strip() for x in (principal_id, capability, target)):
            raise ValueError("invalid grant")
        self._grants.add((principal_id, capability, target))
    def revoke(self, principal_id: str, capability: str, target: str):
        self._grants.discard((principal_id, capability, target))
    def allowed(self, principal_id: str, capability: str, target: str) -> bool:
        return (principal_id, capability, target) in self._grants
