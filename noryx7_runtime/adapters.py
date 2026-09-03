from __future__ import annotations

from typing import Any, Protocol

from .capabilities import CapabilityBroker
from .contracts import ActionEnvelope


class ExecutionAdapter(Protocol):
    agent_id: str

    def execute(self, envelope: ActionEnvelope) -> Any:
        ...


class CapabilityAdapter:
    """Resolve every action through the capability broker before invoking effects."""

    def __init__(self, broker: CapabilityBroker, *, agent_id: str):
        if not isinstance(broker, CapabilityBroker):
            raise TypeError("broker must be a CapabilityBroker")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        self._broker = broker
        self.agent_id = agent_id

    def execute(self, envelope: ActionEnvelope) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope must be an ActionEnvelope")
        if not envelope.execution_id or not envelope.principal_id:
            raise PermissionError("missing execution identity")
        capability = self._broker.resolve(envelope)
        return capability.handler(envelope)
