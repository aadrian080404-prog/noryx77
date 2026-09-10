"""Canonical cross-component integration boundary for NORYX7.

This module does not replace existing security, memory, routing, or verification
components. It binds them through one small coordination surface and keeps the
global fabric digest-only: raw user/task payloads are never persisted here.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from ecosystem.global_fabric import (
    GlobalIdentityAuthorizationFabric,
    GlobalMemoryFabric,
    IdentityAuthorization,
    MemoryLevel,
)
from .identity import AgentIdentity
from .system_identity import CANONICAL_SYSTEM_IDENTITY


class CanonicalSystemFabric:
    """Single integration boundary shared by runtime, gateway, JARVIS and web."""

    POLICY_NAMESPACE = "NORYX7:canonical-system-fabric:v1"

    def __init__(self) -> None:
        self.memory = GlobalMemoryFabric()
        self.identity = GlobalIdentityAuthorizationFabric()
        self.policy_digest = sha256(self.POLICY_NAMESPACE.encode("utf-8")).hexdigest()

    @staticmethod
    def session_id_from_token(token: str) -> str:
        if not isinstance(token, str) or not token:
            raise ValueError("session_token_required")
        return "session:" + sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def agent_session_id(identity: AgentIdentity) -> str:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        fingerprint = sha256(identity.public_key).hexdigest()
        return "agent:" + identity.agent_id + ":" + fingerprint

    def bind_session(self, *, session_id: str, client_id: str, device_id: str = "gateway", role: str = "client", capabilities: tuple[str, ...] = ("execute", "memory:write")) -> IdentityAuthorization:
        if not all(isinstance(value, str) and value.strip() for value in (session_id, client_id, device_id, role)):
            raise ValueError("invalid_session_binding")
        if not isinstance(capabilities, tuple) or not capabilities:
            raise ValueError("invalid_session_capabilities")
        authorization_digest = sha256((f"{session_id}|{client_id}|{device_id}|{role}|{','.join(capabilities)}|{self.policy_digest}").encode("utf-8")).hexdigest()
        authorization = IdentityAuthorization(identity_id=client_id, session_id=session_id, device_id=device_id, role=role, capabilities=capabilities, policy_digest=self.policy_digest, authorization_digest=authorization_digest)
        self.identity.bind(authorization)
        return authorization

    def bind_agent_identity(self, identity: AgentIdentity, *, capabilities: tuple[str, ...] = ("execute",)) -> IdentityAuthorization:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("invalid_agent_identity")
        if not isinstance(capabilities, tuple) or not capabilities:
            raise ValueError("invalid_agent_capabilities")
        return self.bind_session(session_id=self.agent_session_id(identity), client_id=identity.agent_id, device_id="agent-runtime", role="agent", capabilities=capabilities)

    def authorize_agent(self, identity: AgentIdentity, capability: str) -> IdentityAuthorization:
        return self.authorize(self.agent_session_id(identity), capability)

    def authorize(self, session_id: str, capability: str) -> IdentityAuthorization:
        return self.identity.authorize(session_id, capability, self.policy_digest)

    @staticmethod
    def _metadata_digest(metadata: Any) -> str:
        try:
            canonical = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        except Exception as exc:
            raise ValueError("invalid_provenance_metadata") from exc
        return sha256(canonical.encode("utf-8")).hexdigest()

    def record_execution(self, *, execution_id: str, client_id: str, phase: str, metadata: Any, level: MemoryLevel = MemoryLevel.L3_DISTRIBUTED):
        if not all(isinstance(value, str) and value.strip() for value in (execution_id, client_id, phase)):
            raise ValueError("invalid_execution_binding")
        metadata_digest = self._metadata_digest(metadata)
        payload = f"metadata_digest={metadata_digest}".encode("ascii")
        provenance = (f"{CANONICAL_SYSTEM_IDENTITY.system_id}|{CANONICAL_SYSTEM_IDENTITY.creator}|{client_id}|{execution_id}|{phase}").encode("utf-8")
        return self.memory.put(record_id=f"execution:{execution_id}:{phase}", level=level, payload=payload, provenance=provenance, replicas=("runtime", "gateway"))

    def health(self) -> dict[str, Any]:
        return {"system_id": CANONICAL_SYSTEM_IDENTITY.system_id, "creator": CANONICAL_SYSTEM_IDENTITY.creator, "provenance": CANONICAL_SYSTEM_IDENTITY.provenance, "policy_digest": self.policy_digest, "global_memory_records": len(self.memory.snapshot()), "global_identity_bindings": len(self.identity.snapshot())}
