from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Tuple
from uuid import uuid4


class ExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Intent:
    text: str
    principal_id: str
    intent_id: str = ""

    def __post_init__(self) -> None:
        if not self.text.strip() or not self.principal_id.strip():
            raise ValueError("intent requires text and principal")
        if not self.intent_id:
            object.__setattr__(self, "intent_id", uuid4().hex)


@dataclass(frozen=True)
class ExecutionContext:
    execution_id: str
    principal_id: str
    deadline_monotonic: float
    max_actions: int
    status: ExecutionStatus = ExecutionStatus.CREATED

    def __post_init__(self) -> None:
        if not self.execution_id or not self.principal_id:
            raise ValueError("execution context requires identity")
        if self.max_actions < 0:
            raise ValueError("max_actions must be non-negative")


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    action_type: str
    target: str
    parameters: Mapping[str, Any]
    dependencies: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.step_id or not self.action_type or not self.target:
            raise ValueError("plan step is incomplete")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("duplicate step dependency")


@dataclass(frozen=True)
class ActionEnvelope:
    execution_id: str
    principal_id: str
    step_id: str
    action_type: str
    target: str
    parameters: Mapping[str, Any]
    nonce: str


@dataclass(frozen=True)
class Attestation:
    execution_id: str
    principal_id: str
    step_id: str
    agent_id: str
    agent_key_fingerprint: str
    action_digest: str
    output_digest: str
    verified: bool
    detail: str = ""
    signature: bytes = b""
