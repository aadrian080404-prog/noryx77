from threading import RLock

from .agents import Agent
from .routing_policy import MODEL_ORDER, TASK_MODEL_HINTS


class ResourceRouter:
    """Select registered agents through deterministic task-aware resource routing."""

    MODEL_ORDER = MODEL_ORDER
    TASK_MODEL_HINTS = TASK_MODEL_HINTS

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._registration_policy: dict[str, tuple[object, ...]] = {}
        self._lock = RLock()

    @staticmethod
    def _validate_agent(agent: Agent) -> str:
        agent_id = getattr(agent, "agent_id", None)
        run = getattr(agent, "run", None)
        if not isinstance(agent_id, str): raise TypeError("invalid_agent")
        if not agent_id.strip(): raise ValueError("agent_id required")
        if not callable(run): raise TypeError("invalid_agent")
        model_class = getattr(agent, "model_class", "medium")
        if not isinstance(model_class, str) or model_class not in ResourceRouter.MODEL_ORDER: raise ValueError("invalid_model_class")
        capabilities = getattr(agent, "capabilities", ())
        if not isinstance(capabilities, tuple) or any(not isinstance(item, str) or not item.strip() for item in capabilities): raise ValueError("invalid_capabilities")
        capacity_exempt = getattr(agent, "capacity_exempt", False)
        if not isinstance(capacity_exempt, bool): raise ValueError("invalid_capacity_exempt")
        return agent_id

    @staticmethod
    def _callable_fingerprint(callable_obj) -> tuple[object, ...]:
        function = getattr(callable_obj, "__func__", None)
        owner = getattr(callable_obj, "__self__", None)
        return (id(function if function is not None else callable_obj), id(owner) if owner is not None else None)

    @staticmethod
    def _registration_snapshot(agent: Agent) -> tuple[object, ...]:
        return (getattr(agent, "model_class", "medium"), getattr(agent, "capabilities", ()), getattr(agent, "capacity_exempt", False), getattr(agent, "provider_id", None), getattr(agent, "model_id", None), id(getattr(agent, "provider", None)), ResourceRouter._callable_fingerprint(getattr(agent, "run")))

    def _validate_registered_state(self, agent_id: str, agent: Agent) -> None:
        registered = self._registration_policy.get(agent_id)
        if registered is None: raise RuntimeError("missing_registration_policy")
        if self._registration_snapshot(agent) != registered: raise RuntimeError("registered_agent_metadata_mutated")

    def validate_registered(self, agent: Agent) -> None:
        with self._lock:
            agent_id = self._validate_agent(agent)
            if self._agents.get(agent_id) is not agent: raise LookupError("agent_registration_mismatch")
            self._validate_registered_state(agent_id, agent)

    def resolve_execution(self, agent: Agent):
        """Validate registration and capture the exact run callable before execution."""
        with self._lock:
            agent_id = self._validate_agent(agent)
            if self._agents.get(agent_id) is not agent: raise LookupError("agent_registration_mismatch")
            self._validate_registered_state(agent_id, agent)
            return getattr(agent, "run")

    def register(self, agent: Agent) -> None:
        agent_id = self._validate_agent(agent)
        snapshot = self._registration_snapshot(agent)
        with self._lock:
            if agent_id in self._agents: raise ValueError("duplicate_agent_id")
            self._agents[agent_id] = agent
            self._registration_policy[agent_id] = snapshot

    def get(self, agent_id: str):
        if not isinstance(agent_id, str) or not agent_id.strip(): raise ValueError("invalid_agent_id")
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is not None:
                self._validate_agent(agent)
                if getattr(agent, "agent_id", None) != agent_id: raise LookupError("agent_identity_mismatch")
                self._validate_registered_state(agent_id, agent)
            return agent

    def available(self) -> tuple[str, ...]:
        with self._lock:
            for agent_id, agent in self._agents.items():
                if not isinstance(agent_id, str) or not agent_id.strip(): raise RuntimeError("invalid_registered_agent_id")
                try: registered_id = self._validate_agent(agent)
                except (TypeError, ValueError) as exc: raise RuntimeError("invalid_registered_agent") from exc
                if registered_id != agent_id: raise RuntimeError("agent_identity_mismatch")
                self._validate_registered_state(agent_id, agent)
            return tuple(sorted(self._agents))

    def default_id(self) -> str:
        available = self.available()
        if len(available) != 1: raise LookupError("no unique default resource route")
        return available[0]

    def route(self, preferred: str | None = None):
        with self._lock:
            if preferred is not None:
                if not isinstance(preferred, str) or not preferred.strip(): raise ValueError("invalid_preferred_agent_id")
                agent = self._agents.get(preferred)
                if agent is None: raise LookupError("requested agent unavailable")
                self._validate_agent(agent)
                if getattr(agent, "agent_id", None) != preferred: raise LookupError("agent_identity_mismatch")
                self._validate_registered_state(preferred, agent)
                return agent
            available = self.available()
            if len(available) == 1: return self._agents[available[0]]
            raise LookupError("no unambiguous resource route")

    @staticmethod
    def _required_capabilities(task) -> tuple[str, ...]:
        constraints = getattr(task, "constraints", {})
        if not hasattr(constraints, "get"): raise ValueError("invalid_task_constraints")
        required = constraints.get("required_capabilities", ())
        if not isinstance(required, tuple): raise ValueError("invalid_required_capabilities")
        if any(not isinstance(item, str) or not item.strip() for item in required): raise ValueError("invalid_required_capabilities")
        if len(set(required)) != len(required): raise ValueError("duplicate_required_capabilities")
        return required

    def route_for_task(self, task):
        task_type = getattr(task, "task_type", None)
        if not isinstance(task_type, str) or not task_type.strip(): raise ValueError("invalid_task_type")
        required = self.TASK_MODEL_HINTS.get(task_type, "medium")
        required_index = self.MODEL_ORDER.index(required)
        required_capabilities = self._required_capabilities(task)
        with self._lock:
            candidates = []
            for agent_id, agent in self._agents.items():
                self._validate_agent(agent)
                self._validate_registered_state(agent_id, agent)
                model_class = getattr(agent, "model_class", "medium")
                capabilities = getattr(agent, "capabilities", ())
                if self.MODEL_ORDER.index(model_class) < required_index: continue
                if not set(required_capabilities).issubset(capabilities): continue
                candidates.append(agent)
            if not candidates: raise LookupError("no_resource_satisfies_task")
            candidates.sort(key=lambda agent: (self.MODEL_ORDER.index(getattr(agent, "model_class", "medium")), getattr(agent, "agent_id", "")))
            return candidates[0]
