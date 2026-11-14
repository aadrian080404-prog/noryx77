from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


@dataclass(frozen=True)
class Observation:
    environment: str
    observation_id: str
    payload: Any


@dataclass(frozen=True)
class ProposedAction:
    environment: str
    action_id: str
    action_type: str
    target: str
    parameters: Mapping[str, Any]


class ExecutionAdapter(Protocol):
    environment: str

    def observe(self) -> Observation: ...
    def execute(self, action: ProposedAction) -> Any: ...


class ExecutionFabric:
    """Deny-by-default execution substrate.

    Adapters are untrusted capability providers. Registration is explicit,
    action execution is impossible without an installed policy callback, and
    every action is checked immediately before execution.
    """

    def __init__(self, *, authorize: Callable[[ProposedAction], bool]) -> None:
        if not callable(authorize):
            raise TypeError("authorization_callback_required")
        self._authorize = authorize
        self._adapters: dict[str, ExecutionAdapter] = {}

    def register(self, adapter: ExecutionAdapter) -> None:
        environment = getattr(adapter, "environment", "")
        if not isinstance(environment, str) or not environment.strip():
            raise ValueError("environment_required")
        if not callable(getattr(adapter, "observe", None)):
            raise TypeError("observe_required")
        if not callable(getattr(adapter, "execute", None)):
            raise TypeError("execute_required")
        if environment in self._adapters:
            raise ValueError("environment_already_registered")
        self._adapters[environment] = adapter

    def environments(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def observe(self, environment: str) -> Observation:
        adapter = self._adapters.get(environment)
        if adapter is None:
            raise PermissionError("environment_not_registered")
        observation = adapter.observe()
        if not isinstance(observation, Observation):
            raise TypeError("invalid_observation")
        if observation.environment != environment:
            raise RuntimeError("observation_environment_mismatch")
        return observation

    def execute(self, action: ProposedAction) -> Any:
        if not isinstance(action, ProposedAction):
            raise TypeError("proposed_action_required")
        adapter = self._adapters.get(action.environment)
        if adapter is None:
            raise PermissionError("environment_not_registered")
        if not self._authorize(action):
            raise PermissionError("execution_not_authorized")
        return adapter.execute(action)
