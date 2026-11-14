"""Deterministic provider routing with fail-closed capability checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class Provider:
    name: str
    capabilities: frozenset[str]
    handler: Callable[[Any], Any]


class ProviderRouter:
    def __init__(self) -> None:
        self._providers: list[Provider] = []

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    def register(self, provider: Provider) -> None:
        if (
            not isinstance(provider.name, str)
            or not provider.name.strip()
            or not provider.capabilities
            or not callable(provider.handler)
        ):
            raise ValueError("provider_contract_invalid")
        if any(p.name == provider.name for p in self._providers):
            raise ValueError("provider_already_registered")
        self._providers.append(provider)

    def resolve(self, capability: str, *, excluded: frozenset[str] = frozenset()) -> Provider:
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability_required")
        for provider in self._providers:
            if provider.name not in excluded and capability in provider.capabilities:
                return provider
        raise LookupError("no_authorized_provider")

    def execute(self, capability: str, payload: Any, *, excluded: frozenset[str] = frozenset()) -> Any:
        tried = set(excluded)
        while True:
            provider = self.resolve(capability, excluded=frozenset(tried))
            try:
                return provider.handler(payload)
            except Exception:
                tried.add(provider.name)
                if len(tried) >= len(self._providers):
                    raise RuntimeError("provider_failover_exhausted")
