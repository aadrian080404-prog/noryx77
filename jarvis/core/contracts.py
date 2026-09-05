from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

MAX_REQUEST_TEXT = 64 * 1024
MAX_PLAN_STEPS = 256
MAX_STEP_ID = 128
MAX_CAPABILITY = 128
MAX_TARGET = 2048


@dataclass(frozen=True)
class Request:
    text: str
    principal_id: str
    request_id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("request_text_required")
        if len(self.text.encode("utf-8")) > MAX_REQUEST_TEXT:
            raise ValueError("request_text_size_exceeded")
        if not isinstance(self.principal_id, str) or not self.principal_id.strip():
            raise ValueError("principal_id_required")
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id_required")


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    capability: str
    target: str
    parameters: Mapping[str, Any]
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.step_id, str) or not self.step_id.strip() or len(self.step_id) > MAX_STEP_ID:
            raise ValueError("invalid_step_id")
        if not isinstance(self.capability, str) or not self.capability.strip() or len(self.capability) > MAX_CAPABILITY:
            raise ValueError("invalid_capability")
        if not isinstance(self.target, str) or len(self.target) > MAX_TARGET:
            raise ValueError("invalid_target")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters_mapping_required")
        if not isinstance(self.dependencies, tuple) or any(
            not isinstance(dep, str) or not dep.strip() for dep in self.dependencies
        ):
            raise ValueError("invalid_dependencies")


@dataclass(frozen=True)
class Plan:
    request_id: str
    steps: tuple[PlanStep, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id_required")
        if not isinstance(self.steps, tuple) or len(self.steps) > MAX_PLAN_STEPS:
            raise ValueError("plan_capacity_exceeded")
        if any(not isinstance(step, PlanStep) for step in self.steps):
            raise TypeError("plan_step_required")


@dataclass(frozen=True)
class ActionResult:
    step_id: str
    success: bool
    output: Any = None
    error: str = ""
