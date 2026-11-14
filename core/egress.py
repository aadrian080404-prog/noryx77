"""Fail-closed egress policy primitives for NORYX7."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import threading

MAX_RULES = 4096

@dataclass(frozen=True)
class EgressRequest:
    component: str
    host: str
    port: int
    protocol: str = "tcp"

    def __post_init__(self) -> None:
        if not isinstance(self.component, str) or not self.component.strip():
            raise ValueError("invalid_component")
        if not isinstance(self.host, str) or not self.host.strip() or len(self.host.encode()) > 256:
            raise ValueError("invalid_host")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("invalid_port")
        if self.protocol not in {"tcp", "udp"}:
            raise ValueError("invalid_protocol")

class EgressPolicy:
    """Explicit allow-list; unspecified destinations are denied."""
    def __init__(self, *, max_rules: int = MAX_RULES) -> None:
        if isinstance(max_rules, bool) or not isinstance(max_rules, int) or not 0 < max_rules <= MAX_RULES:
            raise ValueError("invalid_egress_capacity")
        self._max_rules = max_rules
        self._rules: set[tuple[str, str, int, str]] = set()
        self._lock = threading.RLock()

    def allow(self, component: str, host: str, port: int, protocol: str = "tcp") -> None:
        request = EgressRequest(component, host, port, protocol)
        try:
            canonical_host = str(ipaddress.ip_address(request.host))
        except ValueError:
            canonical_host = request.host.lower().rstrip(".")
        rule = (request.component, canonical_host, request.port, request.protocol)
        with self._lock:
            if rule not in self._rules and len(self._rules) >= self._max_rules:
                raise OverflowError("egress_capacity")
            self._rules.add(rule)

    def revoke(self, component: str, host: str, port: int, protocol: str = "tcp") -> None:
        request = EgressRequest(component, host, port, protocol)
        canonical_host = request.host.lower().rstrip(".")
        try:
            canonical_host = str(ipaddress.ip_address(canonical_host))
        except ValueError:
            pass
        with self._lock:
            self._rules.discard((request.component, canonical_host, request.port, request.protocol))

    def authorize(self, request: EgressRequest) -> bool:
        try:
            canonical_host = str(ipaddress.ip_address(request.host))
        except ValueError:
            canonical_host = request.host.lower().rstrip(".")
        with self._lock:
            return (request.component, canonical_host, request.port, request.protocol) in self._rules

    def rules(self) -> tuple[tuple[str, str, int, str], ...]:
        with self._lock:
            return tuple(sorted(self._rules))
