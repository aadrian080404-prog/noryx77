from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
import time


@dataclass(frozen=True)
class AgentRuntimeStatus:
    agent_id: str
    role: str
    state: str
    creator: str
    purpose: str
    capabilities: tuple[str, ...]
    last_heartbeat: float


class AgentRuntime:
    """Operational lifecycle registry for the agents hosted by one NORYX7 runtime.

    ONLINE means the agent is registered, identity-trusted and routable by the
    current runtime. It does not claim that an external model provider exists;
    provider availability remains a separate execution concern.
    """

    def __init__(self, router, identity_registry, *, clock=time.monotonic):
        if router is None or identity_registry is None or not callable(clock):
            raise ValueError("invalid_agent_runtime_dependencies")
        self.router = router
        self.identity_registry = identity_registry
        self.clock = clock
        self._lock = RLock()
        self._states: dict[str, AgentRuntimeStatus] = {}
        self._online = False

    def start(self) -> tuple[AgentRuntimeStatus, ...]:
        with self._lock:
            now = float(self.clock())
            statuses = []
            for agent_id in self.router.available():
                agent = self.router.get(agent_id)
                identity = getattr(agent, "identity", None)
                if identity is None or not self.identity_registry.is_trusted(identity):
                    state = "UNTRUSTED"
                else:
                    state = "ONLINE"
                statuses.append(
                    AgentRuntimeStatus(
                        agent_id=agent_id,
                        role=str(getattr(agent, "role", "system")),
                        state=state,
                        creator=str(getattr(agent, "creator", "NORYX7")),
                        purpose=str(getattr(agent, "purpose", "runtime execution")),
                        capabilities=tuple(getattr(agent, "capabilities", ())),
                        last_heartbeat=now,
                    )
                )
            self._states = {item.agent_id: item for item in statuses}
            self._online = bool(statuses) and all(item.state == "ONLINE" for item in statuses)
            return tuple(statuses)

    def heartbeat(self) -> tuple[AgentRuntimeStatus, ...]:
        with self._lock:
            now = float(self.clock())
            refreshed = []
            for agent_id, current in self._states.items():
                agent = self.router.get(agent_id)
                identity = getattr(agent, "identity", None)
                trusted = identity is not None and self.identity_registry.is_trusted(identity)
                refreshed.append(
                    AgentRuntimeStatus(
                        agent_id=current.agent_id,
                        role=current.role,
                        state="ONLINE" if trusted else "UNTRUSTED",
                        creator=current.creator,
                        purpose=current.purpose,
                        capabilities=current.capabilities,
                        last_heartbeat=now,
                    )
                )
            self._states = {item.agent_id: item for item in refreshed}
            self._online = bool(refreshed) and all(item.state == "ONLINE" for item in refreshed)
            return tuple(refreshed)

    def stop(self) -> None:
        with self._lock:
            self._online = False
            self._states = {
                agent_id: AgentRuntimeStatus(
                    agent_id=item.agent_id,
                    role=item.role,
                    state="OFFLINE",
                    creator=item.creator,
                    purpose=item.purpose,
                    capabilities=item.capabilities,
                    last_heartbeat=item.last_heartbeat,
                )
                for agent_id, item in self._states.items()
            }

    @property
    def online(self) -> bool:
        with self._lock:
            return self._online

    def status(self) -> tuple[AgentRuntimeStatus, ...]:
        with self._lock:
            return tuple(self._states[key] for key in sorted(self._states))

    def require_online(self, agent_id: str) -> AgentRuntimeStatus:
        with self._lock:
            item = self._states.get(agent_id)
            if item is None or item.state != "ONLINE":
                raise RuntimeError("agent_offline")
            return item
