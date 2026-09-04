from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

@dataclass(frozen=True)
class Request:
    text: str
    principal_id: str
    request_id: str = field(default_factory=lambda: uuid4().hex)

@dataclass(frozen=True)
class PlanStep:
    step_id: str
    capability: str
    target: str
    parameters: Mapping[str, Any]
    dependencies: tuple[str, ...] = ()

@dataclass(frozen=True)
class Plan:
    request_id: str
    steps: tuple[PlanStep, ...]

@dataclass(frozen=True)
class ActionResult:
    step_id: str
    success: bool
    output: Any = None
    error: str = ""
