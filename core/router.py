from .agents import Agent


class ResourceRouter:
    """Select registered agents through deterministic task-aware resource routing."""

    MODEL_ORDER = ("micro", "small", "medium", "large", "frontier")
    TASK_MODEL_HINTS = {
        "simple": "micro",
        "classification": "small",
        "analysis": "medium",
        "research": "large",
        "reasoning": "large",
        "planning": "large",
        "frontier": "frontier",
    }

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    @staticmethod
    def _validate_agent(agent: Agent) -> str:
        agent_id = getattr(agent, "agent_id", None)
        run = getattr(agent, "run", None)
        if not isinstance(agent_id, str):
            raise TypeError("invalid_agent")
        if not agent_id.strip():
            raise ValueError("agent_id required")
        if not callable(run):
            raise TypeError("invalid_agent")
        model_class = getattr(agent, "model_class", "medium")
        if not isinstance(model_class, str) or model_class not in ResourceRouter.MODEL_ORDER:
            raise ValueError("invalid_model_class")
        capabilities = getattr(agent, "capabilities", ())
        if not isinstance(capabilities, tuple) or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("invalid_capabilities")
        return agent_id

    def register(self, agent: Agent) -> None:
        agent_id = self._validate_agent(agent)
        if agent_id in self._agents:
            raise ValueError("duplicate_agent_id")
        self._agents[agent_id] = agent

    def get(self, agent_id: str):
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("invalid_agent_id")
        agent = self._agents.get(agent_id)
        if agent is not None:
            self._validate_agent(agent)
            if getattr(agent, "agent_id", None) != agent_id:
                raise LookupError("agent_identity_mismatch")
        return agent

    def available(self) -> tuple[str, ...]:
        for agent_id, agent in self._agents.items():
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RuntimeError("invalid_registered_agent_id")
            try:
                registered_id = self._validate_agent(agent)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("invalid_registered_agent") from exc
            if registered_id != agent_id:
                raise RuntimeError("agent_identity_mismatch")
        return tuple(sorted(self._agents))

    def default_id(self) -> str:
        available = self.available()
        if len(available) != 1:
            raise LookupError("no unique default resource route")
        return available[0]

    def route(self, preferred: str | None = None):
        if preferred is not None:
            if not isinstance(preferred, str) or not preferred.strip():
                raise ValueError("invalid_preferred_agent_id")
            agent = self._agents.get(preferred)
            if agent is None:
                raise LookupError("requested agent unavailable")
            self._validate_agent(agent)
            if getattr(agent, "agent_id", None) != preferred:
                raise LookupError("agent_identity_mismatch")
            return agent
        available = self.available()
        if len(available) == 1:
            return self._agents[available[0]]
        raise LookupError("no unambiguous resource route")

    def route_for_task(self, task):
        """Choose the strongest eligible model class for a task, deterministically."""
        task_type = getattr(task, "task_type", None)
        if not isinstance(task_type, str) or not task_type.strip():
            raise ValueError("invalid_task_type")
        required = self.TASK_MODEL_HINTS.get(task_type, "medium")
        required_index = self.MODEL_ORDER.index(required)
        candidates = []
        for agent_id in self.available():
            agent = self._agents[agent_id]
            model_class = getattr(agent, "model_class", "medium")
            if self.MODEL_ORDER.index(model_class) >= required_index:
                candidates.append(agent)
        if not candidates:
            raise LookupError("no_resource_satisfies_task")
        candidates.sort(key=lambda agent: (self.MODEL_ORDER.index(getattr(agent, "model_class", "medium")), getattr(agent, "agent_id", "")))
        return candidates[0]
