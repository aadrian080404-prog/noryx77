"""Canonical multimodal envelopes; payloads stay outside durable state by reference."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib
class Modality(str,Enum): TEXT="text"; IMAGE="image"; AUDIO="audio"; VIDEO="video"; DOCUMENT="document"
@dataclass(frozen=True)
class MediaRef:
    modality:Modality; content_type:str; digest:str; locator:str
    @classmethod
    def create(cls,modality:Modality,content_type:str,locator:str,content:bytes)->"MediaRef":
        if not content_type.strip() or not locator.strip() or not isinstance(content,(bytes,bytearray)): raise ValueError("media_reference_invalid")
        return cls(modality,content_type,hashlib.sha256(bytes(content)).hexdigest(),locator)
@dataclass(frozen=True)
class MultimodalInput:
    items:tuple[MediaRef,...]; request_digest:str
    @classmethod
    def build(cls,items:tuple[MediaRef,...])->"MultimodalInput":
        if not items: raise ValueError("multimodal_input_empty")
        canonical="|".join(f"{x.modality.value}:{x.content_type}:{x.digest}:{x.locator}" for x in items)
        return cls(items,hashlib.sha256(canonical.encode()).hexdigest())
