from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

from .contracts import TaskSpec
from .identity import AgentIdentityAuthority
from .llm.agent import LLMBackedAgent
from .llm.self_knowledge import SelfKnowledgeProvider
from .hypersynth_runtime import HypersynthRuntime
from .memory import MemoryItem
from .planning import Plan, PlanStep, Planner
from .router import ResourceRouter
from .runtime_base import NORYXRuntime as _BaseNORYXRuntime
from .web_research import WebResearchEngine


class RoleLLMBackedAgent(LLMBackedAgent):
    def __init__(self, model_fabric, *, verifier, self_knowledge, identity, agent_id, role):
        self.agent_id = agent_id
        self.role = role
        super().__init__(model_fabric, verifier=verifier, self_knowledge=self_knowledge, identity=identity)

    def _build_prompt(self, task: TaskSpec) -> str:
        prompt = super()._build_prompt(task)
        prompt = prompt.replace(
            "You are generating a response/proposal only; NORYX7 controls authorization, execution, verification and state.",
            "You are an active reasoning agent inside NORYX7. Use the supplied task context and evidence to produce the best verified reasoning for your assigned role. The NORYX7 runtime enforces authorization, execution, verification and state.",
        )
        return prompt + f"\n=== AGENT ROLE ===\n{self.role}\n=== END AGENT ROLE ===\n"


class DualPlanner(Planner):
    def build(self, task: TaskSpec) -> Plan:
        if not isinstance(task, TaskSpec) or not task.is_well_formed():
            raise TypeError("task must be a well-formed TaskSpec")
        primary = PlanStep(f"{task.task_id}:0", task.objective, "compute", task.risk_class)
        secondary = PlanStep(f"{task.task_id}:1", "Independently review, cross-check and improve the primary reasoning for: " + task.objective, "compute", task.risk_class)
        return Plan(task.task_id, (primary, secondary))


class NORYXRuntime(_BaseNORYXRuntime):
    """Integrated facade over the existing controlled runtime."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.research = WebResearchEngine()
        model_fabric = getattr(self, "_model_fabric", None)
        if model_fabric is None:
            return
        old_agents = getattr(self.router, "_agents", None)
        if isinstance(old_agents, dict):
            old_agents.pop("noryx7-llm", None)
        primary_identity, _ = AgentIdentityAuthority.generate("noryx7-primary")
        secondary_identity, _ = AgentIdentityAuthority.generate("noryx7-secondary")
        self.identity_registry.register(primary_identity)
        self.identity_registry.register(secondary_identity)
        primary = RoleLLMBackedAgent(model_fabric, verifier=self.verifier, self_knowledge=SelfKnowledgeProvider(runtime=self), identity=primary_identity, agent_id="noryx7-primary", role="primary_reasoner")
        secondary = RoleLLMBackedAgent(model_fabric, verifier=self.verifier, self_knowledge=SelfKnowledgeProvider(runtime=self), identity=secondary_identity, agent_id="noryx7-secondary", role="independent_reviewer")
        self.router.register(primary)
        self.router.register(secondary)
        cognitive_router = ResourceRouter(identity_registry=self.identity_registry)
        cognitive_router.register(primary)
        cognitive_router.register(secondary)
        self._cognitive_router = cognitive_router
        self.hypersynth = HypersynthRuntime(verifier=self.verifier, router=cognitive_router, audit=self.audit, limits=self.limits, memory=self.memory, recovery=self.recovery, planner=DualPlanner(max_steps=2))

    def run_hypersynth(self, task: TaskSpec, interaction_context=None):
        research = self.research.run(task)
        model_fabric = getattr(self, "_model_fabric", None)
        if model_fabric is None:
            return super().run_hypersynth(task, interaction_context=interaction_context)
        execution_task = replace(task, input={"original_input": task.input, "research": research}, constraints={**dict(getattr(task, "constraints", {}) or {}), "noryx7_integrated": True})
        self._model_fabric = None
        try:
            result = super().run_hypersynth(execution_task, interaction_context=interaction_context)
        finally:
            self._model_fabric = model_fabric
        if isinstance(result, dict):
            result["research"] = research
            result["agent_topology"] = ("noryx7-primary", "noryx7-secondary")
            if result.get("status") == "completed":
                try:
                    execution_id = getattr(task, "execution_id", "") or uuid4().hex
                    self.memory.put(MemoryItem("research:" + execution_id, json.dumps(research, sort_keys=True, ensure_ascii=False, default=str), kind="working", source=getattr(task, "task_id", ""), importance=0.6, execution_id=execution_id))
                except Exception:
                    pass
        return result
