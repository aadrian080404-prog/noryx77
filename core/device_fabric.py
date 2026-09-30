"""Capability-based multi-device registry with explicit online state."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Device:
    device_id:str; capabilities:frozenset[str]; online:bool=True; metadata:tuple[tuple[str,str],...]=()
class DeviceFabric:
    def __init__(self)->None:self._devices={}
    def register(self,device:Device)->None:
        if not device.device_id.strip() or not device.capabilities: raise ValueError("device_contract_invalid")
        if device.device_id in self._devices: raise ValueError("device_already_registered")
        self._devices[device.device_id]=device
    def set_online(self,device_id:str,online:bool)->Device:
        d=self._devices.get(device_id)
        if d is None: raise KeyError("unknown_device")
        d=Device(d.device_id,d.capabilities,bool(online),d.metadata); self._devices[device_id]=d; return d
    def resolve(self,capability:str)->Device:
        if not isinstance(capability,str) or not capability.strip(): raise ValueError("capability_required")
        for d in self._devices.values():
            if d.online and capability in d.capabilities:return d
        raise LookupError("no_online_capable_device")
