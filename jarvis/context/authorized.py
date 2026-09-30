from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
@dataclass(frozen=True)
class ContextItem:
    source_id:str; source_type:str; value:Any; provenance:str
class AuthorizedContext:
    def __init__(self,authorize:Callable[[str],bool])->None:
        if not callable(authorize): raise TypeError("authorization_callback_required")
        self._authorize=authorize; self._sources={}
    def register(self,source_id:str,reader:Callable[[],Any],source_type:str)->None:
        if not source_id.strip() or not source_type.strip() or not callable(reader): raise ValueError("context_source_invalid")
        if source_id in self._sources: raise ValueError("context_source_already_registered")
        self._sources[source_id]=(reader,source_type)
    def acquire(self,source_id:str)->ContextItem:
        if not self._authorize(source_id): raise PermissionError("context_access_denied")
        item=self._sources.get(source_id)
        if item is None: raise PermissionError("context_source_not_registered")
        reader,source_type=item
        return ContextItem(source_id,source_type,reader(),f"authorized:{source_id}")
