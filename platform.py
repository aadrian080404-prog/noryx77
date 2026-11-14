"""Platform-neutral contracts for NORYX7 assistant integration.

A platform adapter translates OS events/APIs into typed requests and executes
only capability-authorized actions. The cognitive core never receives ambient
OS privileges and never invokes platform APIs directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .device import DeviceAction, DeviceRuntimeBoundary

MAX_TEXT = 1024


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_TEXT:
        raise ValueError(f"invalid_{name}")
    return value


class PlatformKind(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    DESKTOP = "desktop"
    EMBEDDED = "embedded"


class InteractionKind(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    NOTIFICATION = "notification"
    SYSTEM_EVENT = "system_event"


@dataclass(frozen=True)
class PlatformRequest:
    request_id: str
    device_id: str
    platform: PlatformKind
    interaction: InteractionKind
    payload: str

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        _text(self.device_id, "device_id")
        _text(self.payload, "payload")


@dataclass(frozen=True)
class PlatformAction:
    action_id: str
    device_id: str
    capability: str
    payload: str
    epoch: int

    def __post_init__(self) -> None:
        _text(self.action_id, "action_id")
        _text(self.device_id, "device_id")
        _text(self.capability, "capability")
        _text(self.payload, "payload")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise ValueError("invalid_epoch")


class PlatformAdapter(Protocol):
    """Minimal adapter boundary; implementation owns platform-specific APIs."""

    platform: PlatformKind

    def receive(self) -> PlatformRequest: ...

    def execute(self, action: PlatformAction) -> bool: ...


class AssistantIntegrationBoundary:
    """Ensures platform integration remains subordinate to the NORYX7 core."""

    def __init__(self, *, device_boundary: DeviceRuntimeBoundary) -> None:
        if not isinstance(device_boundary, DeviceRuntimeBoundary):
            raise TypeError("device_boundary must be a DeviceRuntimeBoundary")
        self._device_boundary = device_boundary

    @property
    def device_boundary(self) -> DeviceRuntimeBoundary:
        return self._device_boundary

    def execute(self, adapter: PlatformAdapter, action: PlatformAction, *, now: int, epoch: int) -> bool:
        if action.epoch != epoch:
            return False
        if not isinstance(adapter.platform, PlatformKind):
            return False
        expected = self._device_boundary.gate.identity.platform
        if expected != adapter.platform.value:
            return False
        device_action = DeviceAction(action.device_id, action.capability, action.action_id, action.epoch)
        if not self._device_boundary.authorize(device_action, now=now, epoch=epoch):
            return False
        return bool(adapter.execute(action))
