from __future__ import annotations

import json
from typing import Any, Protocol, Callable

from core.egress import EgressPolicy, EgressRequest
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
    """Bridge runtime actions to a device platform boundary.

    Network-capable actions are additionally subject to the explicit, fail-closed
    egress policy. The egress gate executes before the platform side effect.
    """

    def __init__(
        self,
        adapter: PlatformAdapter,
        boundary: AssistantIntegrationBoundary,
        *,
        agent_id: str,
        epoch: int = 0,
        clock: Callable[[], int],
        egress_policy: EgressPolicy | None = None,
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
        if egress_policy is not None and not isinstance(egress_policy, EgressPolicy):
            raise TypeError("egress_policy must be an EgressPolicy")
        self._adapter = adapter
        self._boundary = boundary
        self._epoch = epoch
        self._clock = clock
        self._egress_policy = egress_policy
        self.agent_id = agent_id

    def execute(self, envelope: ActionEnvelope) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope must be an ActionEnvelope")
        self._authorize_egress(envelope)
        payload = json.dumps(
            dict(envelope.parameters),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
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

    def _authorize_egress(self, envelope: ActionEnvelope) -> None:
        if not envelope.action_type.startswith("network."):
            return
        if self._egress_policy is None:
            raise PermissionError("egress_policy_required")
        params = dict(envelope.parameters)
        host = params.get("host")
        port = params.get("port")
        protocol = params.get("protocol", "tcp")
        try:
            request = EgressRequest(self.agent_id, host, port, protocol)
        except (TypeError, ValueError) as exc:
            raise PermissionError("invalid_egress_destination") from exc
        if not self._egress_policy.authorize(request):
            raise PermissionError("egress_denied")

    def _device_id(self) -> str:
        identity = self._boundary.device_boundary.gate.identity
        return identity.device_id

    @property
    def epoch(self) -> int:
        return self._epoch
