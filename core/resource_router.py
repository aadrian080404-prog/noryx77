"""Device/edge/cloud resource routing with deterministic policy."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
class ResourceTier(str,Enum): DEVICE="device"; EDGE="edge"; CLOUD="cloud"
@dataclass(frozen=True)
class ResourceRequest: complexity:int; privacy_required:bool=False; latency_sensitive:bool=False
class ResourceRouter:
 def select(self,r:ResourceRequest)->ResourceTier:
  if not 0<=r.complexity<=100: raise ValueError("invalid_complexity")
  if r.privacy_required:return ResourceTier.DEVICE
  if r.latency_sensitive and r.complexity<=60:return ResourceTier.EDGE
  if r.complexity<=25:return ResourceTier.DEVICE
  if r.complexity<=70:return ResourceTier.EDGE
  return ResourceTier.CLOUD
