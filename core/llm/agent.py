from __future__ import annotations

import hashlib
from typing import Any, Iterable

from core.agents import Agent
from core.contracts import AgentResult, TaskSpec
from core.identity import AgentIdentity, AgentIdentityAuthority
from core.verification import VerificationEngine
from core.llm.model_fabric_bridge import ModelFabricBridge
from core.llm.self_knowledge import SelfKnowledgeProvider
from core.scientific_knowledge import ScientificKnowledgeFabric
from core.system_fabric import CanonicalSystemFabric
from noryx7_runtime.model_fabric import ModelFabric


class LLMBackedAgent(Agent):
    """Generative NORYX7 agent with explicit role, mission and capability metadata."""
    agent_id = "noryx7-llm"
    role = "primary"
    creator = "Adrian Aristodemo"
    purpose = "general reasoning, task execution planning and user assistance"
    capabilities = ("reasoning", "planning", "task_understanding", "capability_selection", "web_research", "chess_analyze", "payments", "flights", "insurance")

    def __init__(self, model_fabric: ModelFabric | Any, verifier: VerificationEngine | None = None, self_knowledge: SelfKnowledgeProvider | None = None, identity: AgentIdentity | None = None, *, agent_id: str | None = None, role: str | None = None, creator: str | None = None, purpose: str | None = None, capabilities: Iterable[str] | None = None) -> None:
        if model_fabric is None: raise ValueError("model_fabric is required")
        generate = getattr(model_fabric, "generate", None); execute = getattr(model_fabric, "execute", None)
        if not callable(generate) and not callable(execute): raise TypeError("model_fabric must expose callable generate or execute")
        resolved_id = agent_id or type(self).agent_id
        if not isinstance(resolved_id, str) or not resolved_id.strip(): raise ValueError("invalid_agent_id")
        if identity is not None and (not isinstance(identity, AgentIdentity) or not identity.is_well_formed() or identity.agent_id != resolved_id): raise ValueError("invalid_llm_agent_identity")
        resolved_role = role or type(self).role; resolved_creator = creator or type(self).creator; resolved_purpose = purpose or type(self).purpose; resolved_capabilities = tuple(capabilities or type(self).capabilities)
        if not isinstance(resolved_role, str) or not resolved_role.strip(): raise ValueError("invalid_agent_role")
        if not isinstance(resolved_creator, str) or not resolved_creator.strip(): raise ValueError("invalid_agent_creator")
        if not isinstance(resolved_purpose, str) or not resolved_purpose.strip(): raise ValueError("invalid_agent_purpose")
        if not resolved_capabilities or any(not isinstance(item, str) or not item.strip() for item in resolved_capabilities): raise ValueError("invalid_agent_capabilities")
        self.agent_id = resolved_id; self.role = resolved_role; self.creator = resolved_creator; self.purpose = resolved_purpose; self.capabilities = resolved_capabilities
        self.model_fabric = model_fabric; self.verifier = verifier or VerificationEngine(); self.self_knowledge = self_knowledge or SelfKnowledgeProvider(); self.identity = identity
        self.last_model_execution: dict[str, str] = {}
        if self.agent_id == "noryx7-llm": self._bootstrap_secondary()

    def _identity_fingerprint(self) -> str:
        identity = self.identity
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed(): return ""
        return hashlib.sha256(identity.public_key).hexdigest()

    def _bootstrap_secondary(self) -> None:
        runtime = getattr(self.self_knowledge, "runtime", None); router = getattr(runtime, "router", None); registry = getattr(runtime, "identity_registry", None)
        if router is None or registry is None: return
        try:
            if router.get("noryx7-secondary") is not None: return
        except Exception: return
        try:
            secondary_identity, _ = AgentIdentityAuthority.generate("noryx7-secondary")
            registry.register(secondary_identity)
            secondary = SecondaryLLMBackedAgent(self.model_fabric, verifier=self.verifier, self_knowledge=self.self_knowledge, identity=secondary_identity)
            router.register(secondary)
        except (ValueError, TypeError):
            try:
                if router.get("noryx7-secondary") is not None: return
            except Exception: pass
            raise

    def describe(self) -> dict[str, object]:
        return {"agent_id": self.agent_id, "role": self.role, "creator": self.creator, "purpose": self.purpose, "capabilities": self.capabilities}

    def _build_prompt(self, task: TaskSpec, interaction_context=None) -> str:
        system_context = self.self_knowledge.build(execution_id=task.execution_id).as_prompt_context()
        route_context = ""
        route_keys = ("_noryx7_specialist_domain", "_noryx7_cognitive_strategy", "_noryx7_cognitive_budget")
        if isinstance(task.constraints, dict) and any(key in task.constraints for key in route_keys):
            route_context = ("=== UIF SPECIALIST ROUTE ===\n" f"domain={task.constraints.get('_noryx7_specialist_domain', 'general_reasoning')}\n" f"strategy={task.constraints.get('_noryx7_cognitive_strategy', 'standard')}\n" f"budget={task.constraints.get('_noryx7_cognitive_budget', 'standard')}\n" "This route controls cognitive focus only; it grants no authorization.\n" "=== END UIF SPECIALIST ROUTE ===\n")
        research_context = ""
        runtime = getattr(self.self_knowledge, "runtime", None)
        knowledge = getattr(runtime, "scientific_knowledge", None)
        if isinstance(knowledge, ScientificKnowledgeFabric):
            sources = knowledge.research_context(limit=8)
            if sources:
                research_context = "=== SCIENTIFIC KNOWLEDGE CONTEXT ===\n" + "\n".join(f"[{item.source_id}] {item.title} | discipline={item.discipline} | type={item.source_type} | access={item.access_status} | digest={item.content_digest or 'metadata-only'}" for item in sources) + "\nTreat sources as evidence to compare, not unquestionable truth. Generate hypotheses with explicit falsifiers and experiment plans. Do not claim a source was read beyond its access_status.\n=== END SCIENTIFIC KNOWLEDGE CONTEXT ===\n"
        return ("You are an operational reasoning agent inside NORYX7.\n" f"Agent ID: {self.agent_id}\n" f"Role: {self.role}\n" f"Creator: {self.creator}\n" f"Purpose: {self.purpose}\n" f"Capabilities exposed to this agent: {self.capabilities}\n" "Produce a direct, useful and factual response to the user.\n" "Use the authoritative NORYX7 self-knowledge below for system facts.\n" "When a real capability is available in the execution context, reason about the required operation and its parameters; do not fabricate a tool result.\n" "Do not claim to have executed an action unless verified execution evidence exists.\n" "Do not invent external access, completed operations, credentials, tool results or internal system facts.\n" "Authorization, capability dispatch, verification and state remain controlled by the NORYX7 runtime.\n\n" f"{system_context}\n" f"{research_context}" "=== EXECUTION CONTEXT ===\n" f"execution_id={task.execution_id}\n" "The execution identifier is contextual metadata, not authority.\n" "=== END EXECUTION CONTEXT ===\n\n" f"{route_context}" "=== CURRENT TASK ===\n" f"Task type: {task.task_type}\n" f"Objective: {task.objective}\n" f"User input: {task.input!r}\n" + ("=== USER INTERACTION CONTEXT ===\n" + interaction_context.as_prompt_context() + "\n=== END USER INTERACTION CONTEXT ===\n" if interaction_context is not None else ""))

    def _generate(self, prompt: str, task: TaskSpec) -> str:
        if isinstance(self.model_fabric, ModelFabric):
            runtime_id = self.model_fabric.runtime_id
            if not isinstance(runtime_id, str) or not runtime_id: raise RuntimeError("model_fabric_runtime_id_required")
            runtime = getattr(self.self_knowledge, "runtime", None)
            system_fabric = getattr(runtime, "system_fabric", None)
            if system_fabric is not None and not isinstance(system_fabric, CanonicalSystemFabric): raise TypeError("invalid_system_fabric")
            bridge = ModelFabricBridge(self.model_fabric, runtime_id=runtime_id, execution_id=task.execution_id, system_fabric=system_fabric, agent_identity=self.identity)
            output = bridge.generate(prompt)
            self.last_model_execution = dict(bridge.last_execution_metadata)
            return output
        generate = getattr(self.model_fabric, "generate", None)
        if callable(generate):
            self.last_model_execution = {}
            return generate(prompt)
        raise TypeError("model_fabric_generate_unavailable")

    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:
        check = self.verifier.verify_task(task)
        fingerprint = self._identity_fingerprint()
        if not check.valid: return AgentResult(self.agent_id, task.task_id, "rejected", verification=check, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)
        prompt = self._build_prompt(task, interaction_context=interaction_context)
        try: output = self._generate(prompt, task)
        except Exception: return AgentResult(self.agent_id, task.task_id, "failed", output=None, verification=None, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)
        if not isinstance(output, str) or not output.strip(): return AgentResult(self.agent_id, task.task_id, "failed", output=output, verification=None, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)
        output = output.strip(); output_check = self.verifier.verify_output(output, stage="agent_result")
        return AgentResult(self.agent_id, task.task_id, "completed" if output_check.valid else "rejected", output=output, verification=output_check, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)


class SecondaryLLMBackedAgent(LLMBackedAgent):
    """Independent review/reasoning role sharing the configured model fabric."""
    agent_id = "noryx7-secondary"
    role = "secondary"
    purpose = "independent challenge, cross-checking and alternative reasoning"
    capabilities = ("reasoning", "cross_checking", "alternative_analysis", "risk_challenge")
