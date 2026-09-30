from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class SessionState(str, Enum): IDLE="idle"; ACTIVE="active"; CLOSING="closing"
@dataclass(frozen=True)
class WakeSession:
    session_id: str
    state: SessionState
    wake_source: str
    started_at_ms: int

class SessionController:
    def __init__(self) -> None: self._session: WakeSession|None=None
    @property
    def session(self)->WakeSession|None: return self._session
    def activate(self, session_id:str, wake_source:str, timestamp_ms:int)->WakeSession:
        if not session_id.strip() or not wake_source.strip() or timestamp_ms<0: raise ValueError("invalid_session")
        if self._session and self._session.state is SessionState.ACTIVE: raise RuntimeError("session_already_active")
        self._session=WakeSession(session_id,SessionState.ACTIVE,wake_source,timestamp_ms); return self._session
    def close(self)->None:
        if self._session: self._session=WakeSession(self._session.session_id,SessionState.CLOSING,self._session.wake_source,self._session.started_at_ms)
        self._session=None
