from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from jarvis.perception.audio import WakeEvent
from jarvis.interaction.session import SessionController, WakeSession
@dataclass(frozen=True)
class AgentInput:
    session_id:str; text:str; wake_source:str; metadata:dict[str,Any]
class JarvisInteractionFrontEnd:
    def __init__(self,session_controller:SessionController|None=None)->None: self.sessions=session_controller or SessionController()
    def on_wake(self,event:WakeEvent,*,session_id:str)->WakeSession:
        if event.event_type.value!="clap_pattern": raise ValueError("unsupported_wake_event")
        return self.sessions.activate(session_id,"audio:"+event.event_type.value,event.timestamp_ms)
    def build_input(self,text:str)->AgentInput:
        session=self.sessions.session
        if session is None: raise PermissionError("jarvis_session_inactive")
        if not text.strip(): raise ValueError("input_text_required")
        return AgentInput(session.session_id,text.strip(),session.wake_source,{"verified_wake":True})
