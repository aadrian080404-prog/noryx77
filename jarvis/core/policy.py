from threading import RLock


MAX_ID_BYTES = 256
MAX_GRANTS = 100_000


class Policy:
    """Thread-safe deny-by-default authorization policy with bounded grants."""

    def __init__(self, max_grants: int = MAX_GRANTS):
        if isinstance(max_grants, bool) or not isinstance(max_grants, int) or max_grants < 1:
            raise ValueError("invalid_max_grants")
        self._max_grants = max_grants
        self._grants: set[tuple[str, str, str]] = set()
        self._lock = RLock()

    @staticmethod
    def _valid(value: str) -> bool:
        return isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= MAX_ID_BYTES

    def grant(self, principal_id: str, capability: str, target: str) -> None:
        if not all(self._valid(x) for x in (principal_id, capability, target)):
            raise ValueError("invalid_policy_grant")
        with self._lock:
            entry = (principal_id, capability, target)
            if len(self._grants) >= self._max_grants and entry not in self._grants:
                raise MemoryError("policy_capacity_exceeded")
            self._grants.add(entry)

    def revoke(self, principal_id: str, capability: str, target: str) -> None:
        if not all(self._valid(x) for x in (principal_id, capability, target)):
            raise ValueError("invalid_policy_identity")
        with self._lock:
            self._grants.discard((principal_id, capability, target))

    def authorize(self, principal_id: str, capability: str, target: str) -> bool:
        if not all(self._valid(x) for x in (principal_id, capability, target)):
            return False
        with self._lock:
            return (principal_id, capability, target) in self._grants

    def __len__(self) -> int:
        with self._lock:
            return len(self._grants)
