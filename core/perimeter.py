"""Stateful inbound/outbound perimeter policy primitives."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ipaddress


class TrafficDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass(frozen=True)
class TrafficRequest:
    component: str
    direction: TrafficDirection
    host: str
    port: int
    protocol: str = "tcp"


class PerimeterPolicy:
    """Default-deny perimeter with explicit direction/host/port/protocol rules."""

    def __init__(self) -> None:
        self._rules: set[tuple[str, TrafficDirection, str, int, str]] = set()

    @staticmethod
    def _host(host: str) -> str:
        if not isinstance(host, str) or not host.strip():
            raise ValueError("invalid_host")
        host = host.strip().lower().rstrip(".")
        try:
            return ipaddress.ip_address(host).compressed
        except ValueError:
            if len(host) > 253 or any(not part or len(part) > 63 for part in host.split(".")):
                raise ValueError("invalid_host")
            return host

    def allow(self, component: str, direction: TrafficDirection, host: str, port: int, protocol: str = "tcp") -> None:
        if not component or not isinstance(direction, TrafficDirection) or not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("invalid_traffic_rule")
        protocol = protocol.lower()
        if protocol not in {"tcp", "udp"}:
            raise ValueError("invalid_protocol")
        self._rules.add((component, direction, self._host(host), port, protocol))

    def revoke(self, component: str, direction: TrafficDirection, host: str, port: int, protocol: str = "tcp") -> None:
        self._rules.discard((component, direction, self._host(host), port, protocol.lower()))

    def authorize(self, request: TrafficRequest) -> bool:
        if not isinstance(request, TrafficRequest):
            return False
        try:
            key = (request.component, request.direction, self._host(request.host), request.port, request.protocol.lower())
        except (TypeError, ValueError):
            return False
        return key in self._rules
