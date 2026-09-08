from __future__ import annotations

from typing import Any, Protocol

from core.egress import EgressPolicy, EgressRequest
from core.platform import AssistantIntegrationBoundary, PlatformAction

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
    """Bind platform execution to identity, device capability, and egress policy."""

    def __init__(self, platform: Any, boundary: AssistantIntegrationBoundary, *, agent_id: str, epoch: int, clock, egress_policy: EgressPolicy | None = None) -> None:
        if not isinstance(boundary, AssistantIntegrationBoundary):
            raise TypeError("boundary must be an AssistantIntegrationBoundary")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("invalid_epoch")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if not hasattr(platform, "platform") or not hasattr(platform, "execute"):
            raise TypeError("invalid_platform")
        if egress_policy is not None and not isinstance(egress_policy, EgressPolicy):
            raise TypeError("invalid_egress_policy")
        self.platform = platform
        self.boundary = boundary
        self.agent_id = agent_id
        self.epoch = epoch
        self.clock = clock
        self.egress_policy = egress_policy

    @staticmethod
    def _network_destination(envelope: ActionEnvelope) -> tuple[str, int, str]:
        parameters = envelope.parameters
        if not isinstance(parameters, dict):
            raise PermissionError("invalid_egress_destination")
        host = parameters.get("host")
        port = parameters.get("port")
        protocol = parameters.get("protocol")
        if not isinstance(host, str) or not host.strip():
            raise PermissionError("invalid_egress_destination")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise PermissionError("invalid_egress_destination")
        if protocol not in {"tcp", "udp"}:
            raise PermissionError("invalid_egress_destination")
        return host, port, protocol

    def execute(self, envelope: ActionEnvelope) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope must be an ActionEnvelope")
        if not envelope.execution_id or not envelope.principal_id:
            raise PermissionError("missing execution identity")

        if envelope.action_type == "network.request":
            if self.egress_policy is None:
                raise PermissionError("egress_policy_required")
            host, port, protocol = self._network_destination(envelope)
            if not self.egress_policy.authorize(EgressRequest(self.agent_id, host, port, protocol)):
                raise PermissionError("egress_denied")

        action = PlatformAction(
            action_id=envelope.execution_id + ":" + envelope.step_id + ":" + envelope.nonce,
            device_id=self.boundary.device_boundary.gate.identity.device_id,
            capability=envelope.action_type,
            payload=repr(dict(envelope.parameters)),
            epoch=self.epoch,
        )
        if not self.boundary.execute(self.platform, action, now=int(self.clock()), epoch=self.epoch):
            raise PermissionError("platform_capability_denied")
        return True
