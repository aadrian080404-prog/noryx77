from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class SpeechRequest:
    session_id: str
    text: str
    language: str = "it-IT"
@dataclass(frozen=True)
class SpeechResponse:
    text: str
    provider: str
    verified: bool
class SpeechProvider(Protocol):
    def transcribe(self, audio: bytes, *, language: str) -> str: ...
    def synthesize(self, text: str, *, language: str) -> bytes: ...

class VoiceGateway:
    def __init__(self, provider: SpeechProvider|None=None)->None: self.provider=provider
    def transcribe(self,audio:bytes,*,language="it-IT")->str:
        if self.provider is None: raise RuntimeError("speech_provider_not_configured")
        if not isinstance(audio,(bytes,bytearray)) or not audio: raise ValueError("audio_required")
        text=self.provider.transcribe(bytes(audio),language=language)
        if not isinstance(text,str) or not text.strip(): raise RuntimeError("empty_transcription")
        return text.strip()
    def synthesize(self,text:str,*,language="it-IT")->bytes:
        if self.provider is None: raise RuntimeError("speech_provider_not_configured")
        if not text.strip(): raise ValueError("text_required")
        audio=self.provider.synthesize(text,language=language)
        if not isinstance(audio,(bytes,bytearray)) or not audio: raise RuntimeError("empty_synthesis")
        return bytes(audio)
