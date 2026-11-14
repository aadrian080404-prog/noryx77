"""Bounded agent mesh: cognition coordination without shared authority."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
class AgentRole(str,Enum): PRIMARY="primary"; RESEARCH="research"; CODE="code"; VERIFIER="verifier"; SECURITY="security"
@dataclass(frozen=True)
class AgentNode: agent_id:str; role:AgentRole; personality_id:str|None=None
@dataclass(frozen=True)
class AgentTask: task_id:str; objective:str; required_role:AgentRole
class AgentMesh:
 def __init__(self): self._nodes:dict[str,AgentNode]={}
 def register(self,node:AgentNode)->None:
  if not node.agent_id or node.agent_id in self._nodes: raise ValueError("invalid_or_duplicate_agent")
  self._nodes[node.agent_id]=node
 def route(self,task:AgentTask)->AgentNode:
  candidates=sorted((n for n in self._nodes.values() if n.role is task.required_role),key=lambda n:n.agent_id)
  if not candidates: raise LookupError("no_authorized_agent")
  return candidates[0]
