"""Capability-based multi-device registry with optional NCP trust fencing."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class Device:
    device_id: str
    capabilities: frozenset[str]
    online: bool = True
    metadata: tuple[tuple[str, str], ...] = ()


class DeviceFabric:
    """Resolve devices by capability, optionally requiring active NCP node trust."""

    def __init__(self, continuity_supervisor=None) -> None:
        if continuity_supervisor is not None and not callable(
            getattr(continuity_supervisor, "resolve_all", None)
        ):
            raise TypeError("invalid_continuity_supervisor")
        self._devices: dict[str, Device] = {}
        self._continuity = continuity_supervisor
        self._lock = RLock()

    def set_continuity_supervisor(self, continuity_supervisor) -> None:
        """Enable NCP fencing without discarding already registered devices."""
        if not callable(getattr(continuity_supervisor, "resolve_all", None)):
            raise TypeError("invalid_continuity_supervisor")
        with self._lock:
            self._continuity = continuity_supervisor

    def register(self, device: Device) -> None:
        if not isinstance(device, Device):
            raise TypeError("device_contract_invalid")
        if (
            not isinstance(device.device_id, str)
            or not device.device_id.strip()
            or len(device.device_id.encode("utf-8")) > 256
            or not isinstance(device.capabilities, (set, frozenset))
            or not device.capabilities
            or any(not isinstance(item, str) or not item.strip() for item in device.capabilities)
            or not isinstance(device.online, bool)
        ):
            raise ValueError("device_contract_invalid")
        normalized = Device(
            device.device_id,
            frozenset(device.capabilities),
            device.online,
            tuple(device.metadata),
        )
        with self._lock:
            if normalized.device_id in self._devices:
                raise ValueError("device_already_registered")
            self._devices[normalized.device_id] = normalized

    def set_online(self, device_id: str, online: bool) -> Device:
        if not isinstance(device_id, str) or not device_id.strip() or not isinstance(online, bool):
            raise ValueError("device_state_contract_invalid")
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise KeyError("unknown_device")
            updated = Device(device.device_id, device.capabilities, online, device.metadata)
            self._devices[device_id] = updated
            return updated

    def resolve(self, capability: str) -> Device:
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability_required")
        with self._lock:
            if self._continuity is None:
                candidates = self._devices.values()
            else:
                try:
                    trusted_nodes = self._continuity.resolve_all(capability)
                except Exception as exc:
                    raise LookupError("no_trusted_online_capable_device") from exc
                candidates = (
                    self._devices.get(node.node_id)
                    for node in trusted_nodes
                )
            for device in candidates:
                if (
                    device is not None
                    and device.online
                    and capability in device.capabilities
                ):
                    return device
        if self._continuity is not None:
            raise LookupError("no_trusted_online_capable_device")
        raise LookupError("no_online_capable_device")
