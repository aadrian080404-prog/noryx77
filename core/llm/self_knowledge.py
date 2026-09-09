from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.system_identity import (
    CREATOR_ID,
    CREATOR_RELATIONSHIP,
    IDENTITY_PROVENANCE,
    SYSTEM_ID,
)

NORYX7_CREATOR = CREATOR_ID
NORYX7_IDENTITY = SYSTEM_ID


@dataclass(frozen=True)
class SelfKnowledgeContext:
    """Authoritative, bounded NORYX7 self-description for reasoning agents."""

    identity: Mapping[str, Any]
    architecture: Mapping[str, Any]
    capabilities: tuple[str, ...]
    limitations: tuple[str, ...]
    operational_state: Mapping[str, Any]
    memory: tuple[Mapping[str, Any], ...]

    def as_prompt_context(self) -> str:
        return (
            "=== NORYX7 SELF-KNOWLEDGE — AUTHORITATIVE SYSTEM CONTEXT ===\n"
            "The following information is supplied by NORYX7 itself.\n"
            "Fields marked OFFICIAL_NORYX7 are authoritative system facts.\n"
            "Do not replace authoritative facts with guesses or invented internals.\n\n"
            "[OFFICIAL_NORYX7][IDENTITY]\n"
            f"{dict(self.identity)}\n\n"
            "[OFFICIAL_NORYX7][ARCHITECTURE]\n"
            f"{dict(self.architecture)}\n\n"
            "[OFFICIAL_NORYX7][CAPABILITIES]\n"
            f"{self.capabilities}\n\n"
            "[OFFICIAL_NORYX7][LIMITATIONS]\n"
            f"{self.limitations}\n\n"
            "[OFFICIAL_NORYX7][OPERATIONAL_STATE]\n"
            f"{dict(self.operational_state)}\n\n"
            "[AUTHORIZED_NORYX7_MEMORY]\n"
            f"{tuple(self.memory)}\n\n"
            "AUTHORITY BOUNDARY:\n"
            "The language model has no independent execution authority.\n"
            "Authorization, capability dispatch, verification and state remain under NORYX7 control.\n"
            "The model must never claim an action was executed unless NORYX7 provides verified execution evidence.\n"
            "If information is absent from this context, explicitly say that the information is unavailable.\n"
            "=== END NORYX7 SELF-KNOWLEDGE ===\n"
        )


class SelfKnowledgeProvider:
    """Read-only provider of bounded, authoritative NORYX7 self-knowledge."""

    def __init__(self, *, runtime: Any | None = None, memory_limit: int = 8) -> None:
        if not isinstance(memory_limit, int) or memory_limit < 0:
            raise ValueError("memory_limit must be non-negative")
        self.runtime = runtime
        self.memory_limit = memory_limit

    def build(self, *, execution_id: str = "") -> SelfKnowledgeContext:
        runtime = self.runtime
        identity = {
            "name": NORYX7_IDENTITY,
            "type": "distributed AI platform",
            "role": "controlled intelligence and orchestration system",
            "creator": NORYX7_CREATOR,
            "created_by": NORYX7_CREATOR,
            "creator_relationship": CREATOR_RELATIONSHIP,
            "purpose": "assist the user through reasoning, orchestration and authorized capabilities",
            "authority_model": "reasoning agents cannot bypass runtime authorization",
            "provenance": IDENTITY_PROVENANCE,
        }

        architecture = {
            "layers": (
                "User Understanding", "HYPERSYNTH CORE", "Resource Router",
                "Agent Layer", "Model Fabric", "Real Model", "Verification",
                "Memory / State", "Security / Authorization", "Runtime",
            ),
            "core_components": (
                "NORYXRuntime", "HypersynthRuntime", "AgentCore", "AgentFabric",
                "ModelFabric", "ResourceRouter", "MemoryStore", "VerificationEngine",
                "RuntimeEngine",
            ),
            "pipeline": (
                "user request", "understanding", "HYPERSYNTH CORE",
                "resource routing", "agent/model reasoning", "capability dispatch",
                "verification", "state/memory", "response",
            ),
            "architecture_registry": (
                "ingress", "understanding", "cognition", "planning", "routing",
                "agents", "capabilities", "tools", "memory", "runtime", "security",
                "state", "distribution", "interfaces", "audit", "recovery",
                "performance", "universal intelligence",
            ),
            "provenance": IDENTITY_PROVENANCE,
        }

        capabilities = (
            "language reasoning through configured model providers",
            "task understanding",
            "task decomposition",
            "resource/model routing",
            "verification",
            "controlled memory",
            "identity-bound agent execution",
            "offline execution where configured",
            "metacognitive challenge and reflection",
            "capability registry and tool execution when configured",
        )

        limitations = (
            "no direct authority to execute actions outside the runtime",
            "no unrestricted filesystem or system access",
            "no access to secrets or credentials through self-knowledge",
            "no access to private keys",
            "no automatic authorization bypass",
            "no claim of completed external actions without verified execution",
            "external capability availability depends on configured providers",
            "real payments/bookings require an explicitly configured provider adapter",
        )

        operational_state: dict[str, Any] = {
            "runtime_present": runtime is not None,
            "memory_present": bool(runtime is not None and getattr(runtime, "memory", None) is not None),
            "hypersynth_present": bool(runtime is not None and getattr(runtime, "hypersynth", None) is not None),
            "router_present": bool(runtime is not None and getattr(runtime, "router", None) is not None),
            "identity_registry_present": bool(runtime is not None and getattr(runtime, "identity_registry", None) is not None),
            "offline_configured": bool(runtime is not None and getattr(runtime, "offline", None) is not None),
            "execution_id_bound": bool(execution_id),
            "provenance": IDENTITY_PROVENANCE,
        }

        if runtime is not None:
            router = getattr(runtime, "router", None)
            available = getattr(router, "available", None)
            if callable(available):
                try:
                    agent_ids = tuple(str(agent_id) for agent_id in available())
                    operational_state["registered_agents"] = agent_ids
                    descriptions = []
                    for agent_id in agent_ids:
                        agent = router.get(agent_id)
                        describe = getattr(agent, "describe", None)
                        if callable(describe):
                            try:
                                descriptions.append(describe())
                            except Exception:
                                continue
                    operational_state["agent_fabric"] = tuple(descriptions)
                except Exception:
                    operational_state["registered_agents"] = ()

            tool_executor = getattr(runtime, "tool_executor", None)
            registry = getattr(tool_executor, "capabilities", None)
            names = getattr(registry, "names", None)
            if callable(names):
                try:
                    operational_state["registered_capabilities"] = tuple(names())
                except Exception:
                    operational_state["registered_capabilities"] = ()

        memory = self._safe_memory(runtime, execution_id=execution_id)
        return SelfKnowledgeContext(
            identity=identity,
            architecture=architecture,
            capabilities=capabilities,
            limitations=limitations,
            operational_state=operational_state,
            memory=memory,
        )

    def _safe_memory(self, runtime: Any | None, *, execution_id: str) -> tuple[Mapping[str, Any], ...]:
        if runtime is None or self.memory_limit == 0:
            return ()
        store = getattr(runtime, "memory", None)
        list_method = getattr(store, "list", None) if store is not None else None
        if not callable(list_method) or not execution_id:
            return ()
        try:
            records = list_method(execution_id=execution_id)
        except Exception:
            return ()
        safe: list[Mapping[str, Any]] = []
        for record in tuple(records)[-self.memory_limit:]:
            item = dict(record) if isinstance(record, Mapping) else {"type": type(record).__name__, "value": repr(record)}
            safe.append({
                "source": "NORYX7_MEMORY",
                "provenance": "AUTHORIZED_NORYX7_MEMORY",
                "content": item,
            })
        return tuple(safe)
