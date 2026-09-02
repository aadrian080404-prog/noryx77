from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .contracts import TaskSpec


@dataclass(frozen=True)
class ProviderRequest:
    task_id: str
    task_type: str
    objective: str
    input: Any
    constraints: Mapping[str, Any]


@dataclass(frozen=True)
class ProviderResponse:
    output: Any
    provider_id: str
    model_id: str = ""
    metadata: Mapping[str, Any] = None


class Provider(Protocol):
    provider_id: str

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Execute one bounded request and return an explicit response envelope."""
        ...


class CallableProvider:
    """Adapter for a real model/service callable without coupling the kernel to an SDK."""

    def __init__(self, fn: Callable[[ProviderRequest], Any], *, provider_id: str = "callable", model_id: str = ""):
        if not callable(fn):
            raise TypeError("provider_callable_required")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id_required")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id_required")
        self._fn = fn
        self.provider_id = provider_id
        self.model_id = model_id

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not isinstance(request, ProviderRequest):
            raise TypeError("invalid_provider_request")
        output = self._fn(request)
        return ProviderResponse(output=output, provider_id=self.provider_id, model_id=self.model_id, metadata={})


def request_from_task(task: TaskSpec) -> ProviderRequest:
    if not isinstance(task, TaskSpec) or not task.is_well_formed():
        raise TypeError("task_must_be_well_formed")
    try:
        isolated_input = deepcopy(task.input)
        isolated_constraints = deepcopy(dict(task.constraints))
    except Exception as exc:
        raise TypeError("task_input_not_isolatable") from exc
    return ProviderRequest(
        task_id=task.task_id,
        task_type=task.task_type,
        objective=task.objective,
        input=isolated_input,
        constraints=isolated_constraints,
    )


__all__ = ["Provider", "ProviderRequest", "ProviderResponse", "CallableProvider", "request_from_task"]
