from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from uuid import uuid4

from .contracts import TaskSpec


@dataclass(frozen=True)
class JarvisCapabilities:
    """Platform-neutral capability declaration for the NORYX7 assistant layer."""

    perception: bool = True
    planning: bool = True
    tool_use: bool = True
    memory: bool = True
    verification: bool = True
    multimodal: bool = False
    proactive: bool = False


@dataclass(frozen=True)
class JarvisRequest:
    """A user-level request that is converted into a bounded NORYX7 task."""

    request_id: str
    objective: str
    input: Any = None
    constraints: Mapping[str, Any] = field(default_factory=dict)
    risk_class: str = "normal"
    verification_requirements: tuple[str, ...] = ()
    execution_id: str = ""

    def to_task(self) -> TaskSpec:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("invalid request_id")
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("invalid objective")
        if not isinstance(self.constraints, Mapping):
            raise ValueError("invalid constraints")
        execution_id = self.execution_id or uuid4().hex
        return TaskSpec(
            task_id=self.request_id,
            task_type="jarvis_request",
            objective=self.objective,
            input=self.input,
            constraints=dict(self.constraints),
            verification_requirements=tuple(self.verification_requirements),
            risk_class=self.risk_class,
            execution_id=execution_id,
        )


@dataclass(frozen=True)
class JarvisResponse:
    """Stable, platform-neutral response envelope."""

    request_id: str
    execution_id: str
    status: str
    result: Any = None
    reason: str = ""
    verified: bool = False


class NORYX7RuntimePort(Protocol):
    runtime_id: str

    def run_hypersynth(self, task: TaskSpec) -> Mapping[str, Any]:
        ...


class JarvisAssistant:
    """Thin assistant shell over NORYX7; intelligence remains in NORYX7."""

    def __init__(self, runtime: NORYX7RuntimePort, capabilities: JarvisCapabilities | None = None):
        if runtime is None or not isinstance(getattr(runtime, "runtime_id", None), str):
            raise ValueError("invalid NORYX7 runtime")
        self.runtime = runtime
        self.capabilities = capabilities or JarvisCapabilities()

    def handle(self, request: JarvisRequest) -> JarvisResponse:
        task = request.to_task()
        result = self.runtime.run_hypersynth(task)
        if not isinstance(result, Mapping):
            return JarvisResponse(request.request_id, task.execution_id, "rejected", reason="malformed_runtime_result")

        status = result.get("status")
        if status not in {"completed", "rejected"}:
            return JarvisResponse(request.request_id, task.execution_id, "rejected", reason="invalid_runtime_status")

        verified = bool(result.get("verified", False))
        return JarvisResponse(
            request_id=request.request_id,
            execution_id=task.execution_id,
            status=status,
            result=result.get("result", result.get("results")),
            reason=str(result.get("reason", "")),
            verified=verified,
        )

    def capability_snapshot(self) -> Mapping[str, bool]:
        return {
            "perception": self.capabilities.perception,
            "planning": self.capabilities.planning,
            "tool_use": self.capabilities.tool_use,
            "memory": self.capabilities.memory,
            "verification": self.capabilities.verification,
            "multimodal": self.capabilities.multimodal,
            "proactive": self.capabilities.proactive,
        }
