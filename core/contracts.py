from dataclasses import dataclass, field
from typing import Any, Mapping

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_type: str
    objective: str
    input: Any
    constraints: Mapping[str, Any] = field(default_factory=dict)
    verification_requirements: tuple[str, ...] = ()
    risk_class: str = "normal"

@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    action_type: str
    target: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    risk_class: str = "normal"
    requires_authorization: bool = False

@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    stage: str
    reason: str = ""
    details: tuple[str, ...] = ()

@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    task_id: str
    status: str
    output: Any = None
    verification: VerificationResult | None = None
