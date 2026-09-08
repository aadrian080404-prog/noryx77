from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SelfKnowledgeContext:
    """
    Contesto autorevole con cui NORYX7 descrive sé stesso al componente LLM.

    Il modello riceve esclusivamente informazioni descriptive e autorizzate.
    Non riceve segreti, credenziali, chiavi private, handler o autorità operativa.
    """

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
            "Authorization, execution, verification and state remain under NORYX7 control.\n"
            "The model must never claim an action was executed unless NORYX7 provides verified execution evidence.\n"
            "If information is absent from this context, explicitly say that the information is unavailable.\n"

            "=== END NORYX7 SELF-KNOWLEDGE ===\n"
        )


class SelfKnowledgeProvider:
    """
    Read-only provider of bounded, authoritative NORYX7 self-knowledge.

    This provider may inspect safe descriptive runtime state and authorized
    execution-scoped memory, but never exposes operational handlers, secrets,
    credentials, private keys or security-sensitive implementation material.
    """

    def __init__(
        self,
        *,
        runtime: Any | None = None,
        memory_limit: int = 8,
    ) -> None:
        if not isinstance(memory_limit, int) or memory_limit < 0:
            raise ValueError("memory_limit must be non-negative")

        self.runtime = runtime
        self.memory_limit = memory_limit

    def build(self, *, execution_id: str = "") -> SelfKnowledgeContext:
        runtime = self.runtime

        identity = {
            "name": "NORYX7",
            "type": "distributed AI platform",
            "role": "controlled intelligence and orchestration system",
            "authority_model": "LLM has no direct operational authority",
            "provenance": "OFFICIAL_NORYX7",
        }

        architecture = {
            "layers": (
                "User Understanding",
                "HYPERSYNTH CORE",
                "Resource Router",
                "Agent Layer",
                "Model Fabric",
                "Real Model",
                "Verification",
                "Memory / State",
                "Security / Authorization",
                "Runtime",
            ),
            "core_components": (
                "NORYXRuntime",
                "HypersynthRuntime",
                "AgentCore",
                "AgentFabric",
                "ModelFabric",
                "ResourceRouter",
                "MemoryStore",
                "VerificationEngine",
                "RuntimeEngine",
            ),
            "pipeline": (
                "user request",
                "understanding",
                "HYPERSYNTH CORE",
                "resource routing",
                "agent/model reasoning",
                "verification",
                "state/memory",
                "response",
            ),
            "architecture_registry": (
                "ingress",
                "understanding",
                "cognition",
                "planning",
                "routing",
                "agents",
                "capabilities",
                "tools",
                "memory",
                "runtime",
                "security",
                "state",
                "distribution",
                "interfaces",
                "audit",
                "recovery",
                "performance",
                "universal intelligence",
            ),
            "provenance": "OFFICIAL_NORYX7",
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
        )

        limitations = (
            "no direct authority to execute actions",
            "no unrestricted filesystem or system access",
            "no access to secrets or credentials",
            "no access to private keys",
            "no automatic authorization bypass",
            "no claim of completed external actions without verified execution",
            "provider availability depends on the configured ModelFabric",
            "self-knowledge is limited to authoritative information explicitly exposed by NORYX7",
        )

        operational_state = {
            "runtime_present": runtime is not None,
            "memory_present": bool(
                runtime is not None
                and getattr(runtime, "memory", None) is not None
            ),
            "hypersynth_present": bool(
                runtime is not None
                and getattr(runtime, "hypersynth", None) is not None
            ),
            "router_present": bool(
                runtime is not None
                and getattr(runtime, "router", None) is not None
            ),
            "identity_registry_present": bool(
                runtime is not None
                and getattr(runtime, "identity_registry", None) is not None
            ),
            "offline_configured": bool(
                runtime is not None
                and getattr(runtime, "offline", None) is not None
            ),
            "execution_id_bound": bool(execution_id),
            "provenance": "OFFICIAL_NORYX7",
        }

        if runtime is not None:
            router = getattr(runtime, "router", None)
            available = getattr(router, "available", None)

            if callable(available):
                try:
                    agents = tuple(available())
                    operational_state["registered_agents"] = tuple(
                        str(agent_id) for agent_id in agents
                    )
                except Exception:
                    operational_state["registered_agents"] = ()

        memory = self._safe_memory(
            runtime,
            execution_id=execution_id,
        )

        return SelfKnowledgeContext(
            identity=identity,
            architecture=architecture,
            capabilities=capabilities,
            limitations=limitations,
            operational_state=operational_state,
            memory=memory,
        )

    def _safe_memory(
        self,
        runtime: Any | None,
        *,
        execution_id: str,
    ) -> tuple[Mapping[str, Any], ...]:
        if runtime is None or self.memory_limit == 0:
            return ()

        store = getattr(runtime, "memory", None)
        if store is None:
            return ()

        list_method = getattr(store, "list", None)
        if not callable(list_method):
            return ()

        try:
            if execution_id:
                records = list_method(execution_id=execution_id)
            else:
                return ()
        except Exception:
            return ()

        safe: list[Mapping[str, Any]] = []

        for record in tuple(records)[-self.memory_limit:]:
            if isinstance(record, Mapping):
                item = dict(record)
            else:
                item = {
                    "type": type(record).__name__,
                    "value": repr(record),
                }

            safe.append(
                {
                    "source": "NORYX7_MEMORY",
                    "provenance": "AUTHORIZED_NORYX7_MEMORY",
                    "content": item,
                }
            )

        return tuple(safe)
