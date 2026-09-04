class Policy:
    """Deny by default; callers must provide an explicit grant."""
    def __init__(self):
        self._grants = set()

    def grant(self, principal_id: str, capability: str, target: str) -> None:
        if not all(isinstance(x, str) and x.strip() for x in (principal_id, capability, target)):
            raise ValueError("invalid policy grant")
        self._grants.add((principal_id, capability, target))

    def revoke(self, principal_id: str, capability: str, target: str) -> None:
        self._grants.discard((principal_id, capability, target))

    def authorize(self, principal_id: str, capability: str, target: str) -> bool:
        return (principal_id, capability, target) in self._grants
