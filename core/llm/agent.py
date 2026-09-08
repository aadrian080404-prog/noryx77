from __future__ import annotations

from typing import Any

from core.agents import Agent
from core.contracts import AgentResult, TaskSpec
from core.identity import AgentIdentity
from core.verification import VerificationEngine
from core.llm.model_fabric_bridge import ModelFabricBridge
from core.llm.self_knowledge import SelfKnowledgeProvider
from noryx7_runtime.model_fabric import ModelFabric


class LLMBackedAgent(Agent):
    """
    Agente generativo ufficiale di NORYX7.

    Il modello riceve esclusivamente contesto generativo autorizzato.
    Autorizzazione, strumenti, esecuzione, verifica e stato restano
    sotto il controllo del runtime NORYX7.

    Il ModelFabricBridge viene creato per ogni TaskSpec, così
    runtime_id ed execution_id restano correttamente vincolati
    alla singola esecuzione.
    """

    agent_id = "noryx7-llm"

    def __init__(
        self,
        model_fabric: ModelFabric | Any,
        verifier: VerificationEngine | None = None,
        self_knowledge: SelfKnowledgeProvider | None = None,
        identity: AgentIdentity | None = None,
    ) -> None:
        if model_fabric is None:
            raise ValueError("model_fabric is required")

        generate = getattr(model_fabric, "generate", None)
        execute = getattr(model_fabric, "execute", None)

        if not callable(generate) and not callable(execute):
            raise TypeError(
                "model_fabric must expose callable generate or execute"
            )

        if identity is not None:
            if (
                not isinstance(identity, AgentIdentity)
                or not identity.is_well_formed()
                or identity.agent_id != self.agent_id
            ):
                raise ValueError("invalid_noryx7_llm_agent_identity")

        self.model_fabric = model_fabric
        self.verifier = verifier or VerificationEngine()
        self.self_knowledge = self_knowledge or SelfKnowledgeProvider()

        if identity is not None:
            self.identity = identity

    def _build_prompt(self, task: TaskSpec) -> str:
        system_context = (
            self.self_knowledge
            .build(execution_id=task.execution_id)
            .as_prompt_context()
        )

        return (
            "You are the language reasoning component of NORYX7.\n"
            "Produce a direct, useful and factual response to the user.\n"
            "Use the authoritative NORYX7 self-knowledge below when the "
            "user asks about NORYX7 itself, its architecture, components, "
            "capabilities, limitations or operational state.\n"
            "Do not claim to have executed actions that you did not execute.\n"
            "Do not invent tool results, external access, completed operations, "
            "internal components or system facts.\n"
            "You are generating a response/proposal only; NORYX7 controls "
            "authorization, execution, verification and state.\n\n"
            f"{system_context}\n"
            "=== EXECUTION CONTEXT ===\n"
            "This request belongs to the following bounded NORYX7 execution.\n"
            f"execution_id={task.execution_id}\n"
            "The execution identifier is contextual metadata, not authority.\n"
            "=== END EXECUTION CONTEXT ===\n\n"
            "=== CURRENT TASK ===\n"
            f"Task type: {task.task_type}\n"
            f"Objective: {task.objective}\n"
            f"User input: {task.input!r}\n"
        )

    def _generate(self, prompt: str, task: TaskSpec) -> str:
        if isinstance(self.model_fabric, ModelFabric):
            runtime_id = self.model_fabric.runtime_id
            if not isinstance(runtime_id, str) or not runtime_id:
                raise RuntimeError("model_fabric_runtime_id_required")

            bridge = ModelFabricBridge(
                self.model_fabric,
                runtime_id=runtime_id,
                execution_id=task.execution_id,
            )
            return bridge.generate(prompt)

        generate = getattr(self.model_fabric, "generate", None)
        if callable(generate):
            return generate(prompt)

        raise TypeError("model_fabric_generate_unavailable")

    def run(self, task: TaskSpec) -> AgentResult:
        check = self.verifier.verify_task(task)

        if not check.valid:
            return AgentResult(
                self.agent_id,
                task.task_id,
                "rejected",
                verification=check,
                execution_id=task.execution_id,
            )

        prompt = self._build_prompt(task)

        try:
            output = self._generate(prompt, task)
        except Exception:
            return AgentResult(
                self.agent_id,
                task.task_id,
                "failed",
                output=None,
                verification=None,
                execution_id=task.execution_id,
            )

        if not isinstance(output, str) or not output.strip():
            return AgentResult(
                self.agent_id,
                task.task_id,
                "failed",
                output=output,
                verification=None,
                execution_id=task.execution_id,
            )

        output = output.strip()
        output_check = self.verifier.verify_output(
            output,
            stage="agent_result",
        )

        return AgentResult(
            self.agent_id,
            task.task_id,
            "completed" if output_check.valid else "rejected",
            output=output,
            verification=output_check,
            execution_id=task.execution_id,
        )
