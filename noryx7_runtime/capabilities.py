from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Mapping

from .contracts import ActionEnvelope


CapabilityHandler = Callable[[ActionEnvelope], object]


@dataclass(frozen=True)
class Capability:
    name: str
    action_types: frozenset[str]
    handler: CapabilityHandler

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("invalid capability name")
        if not isinstance(self.action_types, frozenset) or not self.action_types:
            raise ValueError("invalid capability action types")
        if any(not isinstance(action_type, str) or not action_type.strip() for action_type in self.action_types):
            raise ValueError("invalid capability action type")
        if not callable(self.handler):
            raise TypeError("capability handler must be callable")

    def supports(self, action_type: str) -> bool:
        return action_type in self.action_types


class CapabilityBroker:
    """Resolve an action to one immutable, explicitly registered capability."""

    def __init__(self, capabilities: Mapping[str, Capability] | None = None) -> None:
        self._lock = RLock()
        self._capabilities: dict[str, Capability] = {}
        for capability in (capabilities or {}).values():
            self.register(capability)

    def register(self, capability: Capability) -> None:
        if not isinstance(capability, Capability):
            raise TypeError("capability must be a Capability")
        with self._lock:
            if capability.name in self._capabilities:
                raise ValueError("capability already registered")
            self._capabilities[capability.name] = capability

    def resolve(self, envelope: ActionEnvelope) -> Capability:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope must be an ActionEnvelope")
        if not envelope.execution_id or not envelope.principal_id:
            raise PermissionError("missing execution identity")
        if not isinstance(envelope.action_type, str) or not envelope.action_type.strip():
            raise ValueError("invalid action type")
        with self._lock:
            matches = tuple(c for c in self._capabilities.values() if c.supports(envelope.action_type))
        if len(matches) != 1:
            raise LookupError("capability resolution failed")
        return matches[0]

    def execute(self, envelope: ActionEnvelope) -> object:
        capability = self.resolve(envelope)
        return capability.handler(envelope)
