from __future__ import annotations

import json
from typing import Any, Protocol, Callable

from core.platform import AssistantIntegrationBoundary, PlatformAction, PlatformAdapter

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


class PlatformExecutionAdapter:
    """Bridge the runtime action envelope to a device platform boundary.

    The platform adapter never receives an ambient runtime command. Every
    effect is converted into a typed PlatformAction and authorized by the
    AssistantIntegrationBoundary before the platform implementation runs.
    """

    def __init__(
        self,
        adapter: PlatformAdapter,
        boundary: AssistantIntegrationBoundary,
        *,
        agent_id: str,
        epoch: int = 0,
        clock: Callable[[], int],
    ) -> None:
        if not callable(getattr(adapter, "execute", None)):
            raise TypeError("platform adapter must expose execute")
        if not isinstance(boundary, AssistantIntegrationBoundary):
            raise TypeError("boundary must be an AssistantIntegrationBoundary")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("epoch must be a non-negative integer")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._adapter = adapter
        self._boundary = boundary
        self._epoch = epoch
        self._clock = clock
        self.agent_id = agent_id

    def execute(self, envelope: ActionEnvelope) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope must be an ActionEnvelope")
        payload = json.dumps(dict(envelope.parameters), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        action = PlatformAction(
            action_id=envelope.nonce,
            device_id=self._device_id(),
            capability=envelope.action_type,
            payload=payload,
            epoch=self._epoch,
        )
        if not self._boundary.execute(self._adapter, action, now=int(self._clock()), epoch=self._epoch):
            raise PermissionError("platform_action_denied")
        return True

    def _device_id(self) -> str:
        identity = self._boundary.device_boundary.gate.identity
        return identity.device_id

    @property
    def epoch(self) -> int:
        return self._epoch
