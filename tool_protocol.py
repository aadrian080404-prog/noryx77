"""Provider-neutral tool contract with explicit authorization and provenance."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable,Any
@dataclass(frozen=True)
class ToolSpec:
    name:str; version:str; capabilities:frozenset[str]; handler:Callable[[dict[str,Any]],Any]
@dataclass(frozen=True)
class ToolResult:
    tool:str; success:bool; value:Any=None; error:str|None=None; provenance:str=""
class ToolRegistry:
    def __init__(self)->None:self._tools={}
    def register(self,spec:ToolSpec)->None:
        if not spec.name.strip() or not spec.version.strip() or not spec.capabilities or not callable(spec.handler): raise ValueError("tool_contract_invalid")
        if spec.name in self._tools: raise ValueError("tool_already_registered")
        self._tools[spec.name]=spec
    def invoke(self,name:str,args:dict[str,Any],*,authorize:Callable[[ToolSpec],bool])->ToolResult:
        spec=self._tools.get(name)
        if spec is None:return ToolResult(name,False,error="tool_not_found")
        if not callable(authorize) or authorize(spec) is not True:return ToolResult(name,False,error="authorization_denied",provenance="deny")
        if not isinstance(args,dict):return ToolResult(name,False,error="invalid_arguments")
        try:return ToolResult(name,True,value=spec.handler(args),provenance=f"{name}@{spec.version}")
        except Exception as exc:return ToolResult(name,False,error=type(exc).__name__,provenance=f"{name}@{spec.version}")
