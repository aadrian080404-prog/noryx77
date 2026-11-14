"""Device/runtime contracts for running NORYX7 on phones and other clients.

The core remains platform-independent. Concrete Android/iOS/system adapters are
outside this module and receive only explicitly authorized capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MAX_TEXT = 256
MAX_CAPABILITIES = 128


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_TEXT:
        raise ValueError(f"invalid_{name}")
    return value


class DeviceTrust(str, Enum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    REVOKED = "revoked"
    ISOLATED = "isolated"


class DeviceRole(str, Enum):
    CLIENT = "client"
    EDGE = "edge"
    CLOUD = "cloud"


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    platform: str
    role: DeviceRole = DeviceRole.CLIENT
    trust: DeviceTrust = DeviceTrust.UNKNOWN

    def __post_init__(self) -> None:
        _text(self.device_id, "device_id")
        _text(self.platform, "platform")


@dataclass(frozen=True)
class CapabilityGrant:
    capability: str
    audience: str
    expires_at: int
    epoch: int

    def __post_init__(self) -> None:
        _text(self.capability, "capability")
        _text(self.audience, "audience")
        if not isinstance(self.expires_at, int) or self.expires_at < 0:
            raise ValueError("invalid_expiry")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise ValueError("invalid_epoch")


class DeviceCapabilityGate:
    """Fail-closed capability gate for platform adapters."""

    def __init__(self, identity: DeviceIdentity) -> None:
        self.identity = identity
        self._grants: dict[str, CapabilityGrant] = {}

    def grant(self, grant: CapabilityGrant) -> None:
        if len(self._grants) >= MAX_CAPABILITIES and grant.capability not in self._grants:
            raise OverflowError("capability_capacity")
        if grant.audience != self.identity.device_id:
            raise PermissionError("grant_audience_mismatch")
        self._grants[grant.capability] = grant

    def revoke(self, capability: str) -> None:
        _text(capability, "capability")
        self._grants.pop(capability, None)

    def allows(self, capability: str, *, now: int, epoch: int) -> bool:
        grant = self._grants.get(capability)
        return (
            self.identity.trust is DeviceTrust.VERIFIED
            and grant is not None
            and grant.audience == self.identity.device_id
            and grant.epoch == epoch
            and now <= grant.expires_at
        )


@dataclass(frozen=True)
class DeviceAction:
    device_id: str
    capability: str
    action: str
    epoch: int

    def __post_init__(self) -> None:
        _text(self.device_id, "device_id")
        _text(self.capability, "capability")
        _text(self.action, "action")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise ValueError("invalid_epoch")


class DeviceRuntimeBoundary:
    """Adapter-facing boundary: no model output is a device command."""

    def __init__(self, gate: DeviceCapabilityGate) -> None:
        self.gate = gate

    def authorize(self, action: DeviceAction, *, now: int, epoch: int) -> bool:
        if action.device_id != self.gate.identity.device_id:
            return False
        return self.gate.allows(action.capability, now=now, epoch=epoch)
