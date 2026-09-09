"""Bridge the bounded core runtime into the global ecosystem fabrics."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .global_fabric import (
    GlobalIdentityAuthorizationFabric,
    GlobalMemoryFabric,
    IdentityAuthorization,
    MemoryLevel,
)


@dataclass(frozen=True)
class OperationalFabricSnapshot:
    runtime_id: str
    online_agents: tuple[str, ...]
    memory_records: int
    identity_bindings: int


class OperationalEcosystemBridge:
    """Connect core execution provenance to the global identity/memory indexes.

    The global fabrics remain indexes/contracts: this bridge never grants new
    authority, stores raw model output remotely, or bypasses core verification.
    """

    POLICY_DOMAIN = b"noryx7/operational-policy/v1"

    def __init__(self, *, runtime_id: str, identity_registry, memory) -> None:
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise ValueError("runtime_id_required")
        self.runtime_id = runtime_id
        self.identity_registry = identity_registry
        self.memory = memory
        self.identity = GlobalIdentityAuthorizationFabric()
        self.memory_index = GlobalMemoryFabric()

    @classmethod
    def _policy_digest(cls) -> str:
        return hashlib.sha256(cls.POLICY_DOMAIN).hexdigest()

    def bind_agent(self, *, agent_id: str, role: str, capabilities: tuple[str, ...] = ()) -> None:
        """Mirror a trusted core agent into the global authorization index."""
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id_required")
        if not isinstance(role, str) or not role.strip():
            raise ValueError("agent_role_required")
        if not isinstance(capabilities, tuple):
            capabilities = tuple(capabilities)

        def _bind(identity) -> None:
            capability_tuple = tuple(sorted({str(item) for item in capabilities if str(item).strip()}))
            material = {
                "identity_id": identity.agent_id,
                "session_id": identity.agent_id,
                "device_id": "runtime:" + self.runtime_id,
                "role": role,
                "capabilities": capability_tuple,
                "policy_digest": self._policy_digest(),
            }
            authorization_digest = hashlib.sha256(
                json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            self.identity.bind(
                IdentityAuthorization(
                    identity_id=identity.agent_id,
                    session_id=identity.agent_id,
                    device_id="runtime:" + self.runtime_id,
                    role=role,
                    capabilities=capability_tuple,
                    policy_digest=self._policy_digest(),
                    authorization_digest=authorization_digest,
                )
            )

        self.identity_registry.with_trusted_identity(agent_id, _bind)

    def record_result(self, *, task_id: str, execution_id: str, agent_id: str, output: Any) -> None:
        """Index a verified result without copying its raw payload into global memory."""
        if not all(isinstance(value, str) and value.strip() for value in (task_id, execution_id, agent_id)):
            raise ValueError("execution_provenance_required")
        if not isinstance(output, str) or not output.strip():
            raise ValueError("verified_output_required")
        payload = output.encode("utf-8")
        provenance = json.dumps(
            {
                "task_id": task_id,
                "execution_id": execution_id,
                "agent_id": agent_id,
                "runtime_id": self.runtime_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.memory_index.put(
            "execution:" + execution_id,
            MemoryLevel.L3_DISTRIBUTED,
            payload,
            provenance,
            ("runtime:" + self.runtime_id, "agent:" + agent_id),
        )

    def snapshot(self, *, online_agents: tuple[str, ...]) -> OperationalFabricSnapshot:
        return OperationalFabricSnapshot(
            runtime_id=self.runtime_id,
            online_agents=tuple(online_agents),
            memory_records=len(self.memory_index.snapshot()),
            identity_bindings=len(self.identity.snapshot()),
        )
