"""Resilient provider execution with bounded retry/failover and provenance.

Routing remains deterministic; authorization is evaluated by the execution
fabric for every attempt. A failed provider is excluded for subsequent attempts.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from core.execution_fabric import ExecutionFabric, ProposedAction
from core.provider_router import ProviderRouter, Provider

@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    attempt: int
    success: bool
    error: str | None = None

@dataclass(frozen=True)
class ResilientProviderResult:
    output: Any
    provider: str
    attempts: tuple[ProviderAttempt, ...]

class ResilientProviderExecutor:
    def __init__(self, router: ProviderRouter | None = None, *, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("invalid_max_attempts")
        self.router = router or ProviderRouter()
        self.max_attempts = max_attempts

    def register(self, provider: Provider) -> None:
        self.router.register(provider)

    def execute(
        self,
        capability: str,
        payload: Any,
        *,
        principal_id: str,
        logical_target: str,
        authorize: Callable[[str, str, str], bool],
    ) -> ResilientProviderResult:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise PermissionError("provider_principal_required")
        excluded: set[str] = set()
        attempts: list[ProviderAttempt] = []
        for attempt in range(1, self.max_attempts + 1):
            provider = self.router.resolve(capability, excluded=frozenset(excluded))
            action = ProposedAction(
                environment=provider.name,
                action_id=f"provider:{principal_id}:{provider.name}:{capability}:{attempt}",
                action_type=capability,
                target=logical_target,
                parameters={"payload": payload},
            )
            fabric = ExecutionFabric(
                authorize=lambda a: authorize(principal_id, "provider_execute", logical_target)
            )
            class Adapter:
                environment = provider.name
                def observe(self):
                    from core.execution_fabric import Observation
                    return Observation(environment=self.environment, observation_id=f"provider:{self.environment}", payload={})
                def execute(self, action):
                    return provider.handler(dict(action.parameters))
            fabric.register(Adapter())
            try:
                output = fabric.execute(action)
            except Exception as exc:
                excluded.add(provider.name)
                attempts.append(ProviderAttempt(provider.name, attempt, False, type(exc).__name__))
                if len(excluded) >= len(self.router._providers):
                    raise RuntimeError("provider_failover_exhausted")
                continue
            attempts.append(ProviderAttempt(provider.name, attempt, True))
            return ResilientProviderResult(output, provider.name, tuple(attempts))
        raise RuntimeError("provider_failover_exhausted")
