"""Provider routing bound to the canonical deny-by-default execution fabric.

The gateway deliberately keeps provider discovery (ProviderRouter) separate from
execution authorization/dispatch (ExecutionFabric). A provider is never called
unless the logical JARVIS capability is authorized immediately before dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.execution_fabric import ExecutionFabric, Observation, ProposedAction
from core.provider_router import Provider, ProviderRouter


@dataclass(frozen=True)
class ProviderExecutionResult:
    provider: str
    capability: str
    output: Any


class _ProviderAdapter:
    def __init__(self, provider: Provider) -> None:
        self.provider = provider
        self.environment = provider.name

    def observe(self) -> Observation:
        return Observation(
            environment=self.environment,
            observation_id=f"provider:{self.environment}",
            payload={"provider": self.environment},
        )

    def execute(self, action: ProposedAction) -> Any:
        if action.environment != self.provider.name:
            raise PermissionError("provider_environment_mismatch")
        return self.provider.handler(dict(action.parameters))


class ProviderExecutionGateway:
    """ProviderRouter -> ExecutionFabric bridge with per-call authorization."""

    def __init__(self, router: ProviderRouter | None = None) -> None:
        self.router = router or ProviderRouter()
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        self.router.register(provider)
        self._providers[provider.name] = provider

    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def execute(
        self,
        capability: str,
        payload: Any,
        *,
        principal_id: str,
        logical_target: str,
        authorize: Callable[[str, str, str], bool],
    ) -> ProviderExecutionResult:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise PermissionError("provider_principal_required")
        if not callable(authorize):
            raise TypeError("provider_authorizer_required")

        provider = self.router.resolve(capability)

        adapter = _ProviderAdapter(provider)
        fabric = ExecutionFabric(
            authorize=lambda action: authorize(
                principal_id,
                capability,
                logical_target,
            )
        )
        fabric.register(adapter)

        action = ProposedAction(
            environment=provider.name,
            action_id=f"provider:{principal_id}:{provider.name}:{capability}",
            action_type=capability,
            target=logical_target,
            parameters={"payload": payload},
        )
        output = fabric.execute(action)
        return ProviderExecutionResult(
            provider=provider.name,
            capability=capability,
            output=output,
        )
