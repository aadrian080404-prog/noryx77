"""Bounded L0-L5 memory hierarchy with explicit promotion."""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
class MemoryLevel(IntEnum): L0=0; L1=1; L2=2; L3=3; L4=4; L5=5
@dataclass(frozen=True)
class MemoryRecord: key:str; value:str; level:MemoryLevel
class MemoryHierarchy:
 def __init__(self,max_records:int=100000):
  if not 1<=max_records<=1_000_000: raise ValueError("invalid_memory_capacity")
  self._max=max_records; self._data:dict[str,MemoryRecord]={}
 def put(self,r:MemoryRecord)->None:
  if not r.key or len(r.value)>1_000_000: raise ValueError("invalid_memory_record")
  if r.key not in self._data and len(self._data)>=self._max: raise MemoryError("memory_capacity_reached")
  self._data[r.key]=r
 def get(self,key:str)->MemoryRecord|None:return self._data.get(key)
 def promote(self,key:str,level:MemoryLevel)->MemoryRecord:
  old=self._data[key]; new=MemoryRecord(old.key,old.value,level); self._data[key]=new; return new
