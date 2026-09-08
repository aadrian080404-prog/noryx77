from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol

from .agent_identity import AgentMission, mission_for_agent

class AgentPhase(str, Enum):
    IDLE="idle"; UNDERSTANDING="understanding"; PLANNING="planning"; AUTHORIZING="authorizing"; ACTING="acting"; OBSERVING="observing"; VERIFYING="verifying"; REFLECTING="reflecting"; RESPONDING="responding"; FAILED="failed"
class InteractionMode(str, Enum): TEXT="text"; VOICE="voice"
@dataclass(frozen=True)
class AgentInput:
    content:str; mode:InteractionMode=InteractionMode.TEXT; context:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not isinstance(self.content,str) or not self.content.strip(): raise ValueError("content must be non-empty")
        if len(self.content.encode("utf-8"))>64*1024: raise ValueError("input exceeds 64KiB")
        if not isinstance(self.mode,InteractionMode): raise TypeError("mode must be InteractionMode")
        if len(self.context)>128: raise ValueError("context exceeds 128 items")
@dataclass(frozen=True)
class AgentContext:
    objective:str; input:AgentInput; facts:Mapping[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class AgentPlan:
    steps:tuple[str,...]
    def __post_init__(self):
        if not self.steps or len(self.steps)>64 or any(not isinstance(s,str) or not s.strip() for s in self.steps): raise ValueError("invalid agent plan")
@dataclass(frozen=True)
class AgentResponse:
    content:str; mode:InteractionMode; phase:AgentPhase=AgentPhase.RESPONDING; verified:bool=False
class AgentBrain(Protocol):
    def understand(self,request:AgentInput)->AgentContext:...
    def plan(self,context:AgentContext)->AgentPlan:...
    def act(self,step:str,context:AgentContext)->Any:...
    def verify(self,step:str,result:Any,context:AgentContext)->bool:...
    def reflect(self,context:AgentContext,results:tuple[Any,...])->Any:...
    def respond(self,context:AgentContext,reflection:Any,results:tuple[Any,...])->AgentResponse:...
AuthorizationHook=Callable[[str,AgentContext],bool]
class AgentTransport(Protocol):
    def deliver(self,response:AgentResponse)->AgentResponse:...
class TextTransport:
    def deliver(self,response:AgentResponse)->AgentResponse:return response
class VoiceTransport:
    def deliver(self,response:AgentResponse)->AgentResponse:return response
class AgentOperatingManual:
    PHASES=(AgentPhase.UNDERSTANDING,AgentPhase.PLANNING,AgentPhase.AUTHORIZING,AgentPhase.ACTING,AgentPhase.OBSERVING,AgentPhase.VERIFYING,AgentPhase.REFLECTING,AgentPhase.RESPONDING)
class AgentCore:
    def __init__(self,agent_id:str,brain:AgentBrain,authorize:AuthorizationHook|None=None,transport:AgentTransport|None=None,max_steps:int=64)->None:
        if not isinstance(agent_id,str) or not agent_id: raise ValueError("agent_id must be non-empty")
        if not isinstance(max_steps,int) or isinstance(max_steps,bool) or max_steps<1: raise ValueError("max_steps must be positive")
        self.agent_id,self.brain,self.authorize,self.transport,self.max_steps=agent_id,brain,authorize,transport,max_steps
        self._mission:AgentMission=mission_for_agent(agent_id); self._phase=AgentPhase.IDLE; self._last_failure=None; self._lock=RLock()
    @property
    def phase(self)->AgentPhase:
        with self._lock:return self._phase
    @property
    def last_failure(self)->str|None:
        with self._lock:return self._last_failure
    @property
    def mission(self)->AgentMission:return self._mission
    def _set_phase(self,phase:AgentPhase)->None:self._phase=phase
    def reset(self)->None:
        with self._lock:
            if self._phase is not AgentPhase.FAILED: raise ValueError("agent_not_failed")
            self._phase=AgentPhase.IDLE; self._last_failure=None
    def run(self,request:AgentInput)->AgentResponse:
        with self._lock:
            if self._phase is AgentPhase.FAILED: raise RuntimeError("agent_failed_requires_reset")
            if self._phase is not AgentPhase.IDLE: raise RuntimeError("agent_busy")
            try:
                self._set_phase(AgentPhase.UNDERSTANDING); context=self.brain.understand(request)
                self._set_phase(AgentPhase.PLANNING); plan=self.brain.plan(context)
                if len(plan.steps)>self.max_steps: raise ValueError("agent_step_budget_exceeded")
                results=[]
                for step in plan.steps:
                    self._set_phase(AgentPhase.AUTHORIZING)
                    if self.authorize is not None and not self.authorize(step,context): raise PermissionError("agent_action_denied")
                    self._set_phase(AgentPhase.ACTING); result=self.brain.act(step,context)
                    self._set_phase(AgentPhase.OBSERVING); self._set_phase(AgentPhase.VERIFYING)
                    if not self.brain.verify(step,result,context): raise PermissionError("agent_result_unverified")
                    results.append(result)
                self._set_phase(AgentPhase.REFLECTING); reflection=self.brain.reflect(context,tuple(results))
                self._set_phase(AgentPhase.RESPONDING); response=self.brain.respond(context,reflection,tuple(results))
                if not isinstance(response,AgentResponse) or not response.verified or response.phase is not AgentPhase.RESPONDING: raise PermissionError("agent_response_unverified")
                if self.transport is not None: response=self.transport.deliver(response)
                self._set_phase(AgentPhase.IDLE); return response
            except Exception as exc:
                self._last_failure=type(exc).__name__; self._set_phase(AgentPhase.FAILED); raise
class AgentRegistry:
    def __init__(self,max_agents:int=1024):
        if not isinstance(max_agents,int) or isinstance(max_agents,bool) or max_agents<1: raise ValueError("max_agents must be positive")
        self._max_agents=max_agents; self._agents={}; self._lock=RLock()
    def register(self,agent:AgentCore)->None:
        if not isinstance(agent,AgentCore): raise TypeError("agent must be AgentCore")
        with self._lock:
            if agent.agent_id in self._agents: raise ValueError("duplicate agent")
            if len(self._agents)>=self._max_agents: raise OverflowError("agent registry capacity exceeded")
            self._agents[agent.agent_id]=agent
    def get(self,agent_id:str)->AgentCore:
        with self._lock:return self._agents[agent_id]
    def snapshot(self)->tuple[AgentCore,...]:
        with self._lock:return tuple(self._agents[key] for key in sorted(self._agents))
