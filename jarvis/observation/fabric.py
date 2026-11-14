from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
@dataclass(frozen=True)
class ObservationEvent:
    source_id:str; timestamp_ms:int; kind:str; payload:Any; provenance:str
class ObservationFabric:
    def __init__(self,authorize:Callable[[str],bool])->None:
        if not callable(authorize): raise TypeError("authorization_callback_required")
        self._authorize=authorize; self._readers={}
    def register(self,source_id:str,reader:Callable[[],Any])->None:
        if not source_id.strip() or not callable(reader): raise ValueError("observation_source_invalid")
        if source_id in self._readers: raise ValueError("observation_source_already_registered")
        self._readers[source_id]=reader
    def observe(self,source_id:str,*,timestamp_ms:int,kind:str)->ObservationEvent:
        if not self._authorize(source_id): raise PermissionError("observation_access_denied")
        if source_id not in self._readers: raise PermissionError("observation_source_not_registered")
        if timestamp_ms<0 or not kind.strip(): raise ValueError("observation_contract_invalid")
        return ObservationEvent(source_id,timestamp_ms,kind,self._readers[source_id](),f"authorized:{source_id}")
