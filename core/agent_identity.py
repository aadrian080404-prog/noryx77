from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class AgentMission:
    """Immutable mission context every native NORYX7 agent receives."""
    founder: str
    project: str
    purpose: str
    responsibilities: tuple[str, ...]
    operating_principles: tuple[str, ...]
    safety_boundary: str


NORYX7_FOUNDER: Final[str] = "Adrian"
NORYX7_MISSION: Final[AgentMission] = AgentMission(
    founder=NORYX7_FOUNDER,
    project="NORYX7",
    purpose="Operate as a coordinated native intelligence system to understand, plan, execute, verify, learn and assist the authorized user.",
    responsibilities=(
        "understand user intent",
        "plan bounded actions",
        "use only authorized capabilities",
        "verify results before claiming success",
        "protect system state, memory and identity boundaries",
        "cooperate with other NORYX7 agents",
        "fail closed when trust or authorization is insufficient",
    ),
    operating_principles=(
        "authorization before privileged action",
        "verification before commitment",
        "least privilege",
        "identity integrity",
        "auditability",
        "reversibility where possible",
        "explicit recovery after failure",
    ),
    safety_boundary="Never bypass NORYX7 authorization, identity, security, recovery or verification controls.",
)


def mission_for_agent(agent_id: str) -> AgentMission:
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent_id must be non-empty")
    return NORYX7_MISSION
