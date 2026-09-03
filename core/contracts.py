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
    execution_id: str = ""

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.task_id, str) and bool(self.task_id.strip())
            and isinstance(self.task_type, str) and bool(self.task_type.strip())
            and isinstance(self.objective, str) and bool(self.objective.strip())
            and isinstance(self.constraints, Mapping)
            and isinstance(self.verification_requirements, tuple)
            and all(isinstance(item, str) and bool(item.strip()) for item in self.verification_requirements)
            and isinstance(self.risk_class, str) and bool(self.risk_class.strip())
            and isinstance(self.execution_id, str) and 0 < len(self.execution_id.encode("utf-8")) <= 256
        )


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    action_type: str
    target: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    risk_class: str = "normal"
    requires_authorization: bool = False
    execution_id: str = ""

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.action_id, str) and bool(self.action_id.strip())
            and isinstance(self.action_type, str) and bool(self.action_type.strip())
            and isinstance(self.target, str)
            and isinstance(self.parameters, Mapping)
            and isinstance(self.risk_class, str) and bool(self.risk_class.strip())
            and isinstance(self.requires_authorization, bool)
            and isinstance(self.execution_id, str) and len(self.execution_id.encode("utf-8")) <= 256
        )


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    stage: str
    reason: str = ""
    details: tuple[str, ...] = ()

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.valid, bool)
            and isinstance(self.stage, str) and bool(self.stage.strip())
            and isinstance(self.reason, str)
            and isinstance(self.details, tuple)
            and all(isinstance(item, str) for item in self.details)
        )


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    task_id: str
    status: str
    output: Any = None
    verification: VerificationResult | None = None
    execution_id: str = ""

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.agent_id, str) and bool(self.agent_id.strip())
            and isinstance(self.task_id, str) and bool(self.task_id.strip())
            and isinstance(self.status, str) and bool(self.status.strip())
            and (self.verification is None or isinstance(self.verification, VerificationResult))
            and isinstance(self.execution_id, str) and len(self.execution_id.encode("utf-8")) <= 256
        )
