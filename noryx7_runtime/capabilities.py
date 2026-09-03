from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .contracts import ActionEnvelope


CapabilityHandler = Callable[[ActionEnvelope], object]


@dataclass(frozen=True)
class Capability:
    name: str
    action_types: frozenset[str]
    handler: CapabilityHandler

    def supports(self, action_type: str) -> bool:
        return action_type in self.action_types


class CapabilityBroker:
    """Resolve an action to an explicitly registered capability.

    The broker never falls back to arbitrary callables: an action type must
    have a registered capability and the selected handler is returned only
    after the envelope is checked for a non-empty execution identity.
    """

    def __init__(self, capabilities: Mapping[str, Capability] | None = None) -> None:
        self._capabilities = dict(capabilities or {})

    def register(self, capability: Capability) -> None:
        if not capability.name.strip() or not capability.action_types:
            raise ValueError("invalid capability")
        if capability.name in self._capabilities:
            raise ValueError("capability already registered")
        self._capabilities[capability.name] = capability

    def resolve(self, envelope: ActionEnvelope) -> Capability:
        if not envelope.execution_id or not envelope.principal_id:
            raise PermissionError("missing execution identity")
        matches = [c for c in self._capabilities.values() if c.supports(envelope.action_type)]
        if len(matches) != 1:
            raise LookupError("capability resolution failed")
        return matches[0]

    def execute(self, envelope: ActionEnvelope) -> object:
        return self.resolve(envelope).handler(envelope)
