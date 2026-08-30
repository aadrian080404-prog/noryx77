from __future__ import annotations

from typing import Any

from models.memory import MemoryStore
from models.provider import ModelProvider, MockModelProvider
from models.selector import ResourceSelector
from reasoning.decomposition import TaskDecomposer

from .state import NORYXState


class NORYXOrchestrator:
    """
    Coordinatore centrale di NORYX7.

    Gestisce input, obiettivo, scomposizione e risposta modellata.
    """

    def __init__(
        self,
        model_provider: ModelProvider | None = None,
        decomposer: TaskDecomposer | None = None,
        resource_selector: ResourceSelector | None = None,
        memory_store: MemoryStore | None = None,
    ):
        self.state = NORYXState()
        self.model_provider = model_provider if model_provider is not None else MockModelProvider()
        self.decomposer = decomposer if decomposer is not None else TaskDecomposer()
        self.resource_selector = resource_selector if resource_selector is not None else ResourceSelector()
        self.memory_store = memory_store if memory_store is not None else MemoryStore()

    def receive(self, user_input: str):
        """Riceve un nuovo input e aggiorna lo stato."""
        self.state.user_input = user_input
        self.state.status = "processing"
        return self.state

    def set_goal(self, goal: str):
        """Imposta l'obiettivo del compito."""
        self.state.goal = goal
        return self.state

    def _build_prompt(self) -> str:
        prompt_lines = []

        if self.state.goal:
            prompt_lines.append(f"Goal: {self.state.goal}")

        if self.state.user_input:
            prompt_lines.append(f"User input: {self.state.user_input}")

        prompt_lines.append("Subtasks:")
        prompt_lines.extend(f"- {task}" for task in self.state.subtasks)
        return "\n".join(prompt_lines)

    def _build_task_prompt(self, task: str, memory_context: list[str] | None = None) -> str:
        prompt_lines = [
            f"Goal: {self.state.goal}",
            f"User input: {self.state.user_input}",
            "Current task:",
            f"- {task}",
        ]

        if memory_context:
            prompt_lines.append("Relevant memory:")
            prompt_lines.extend(f"- {entry}" for entry in memory_context)

        return "\n".join(prompt_lines)

    def select_next_task(self) -> str | None:
        """Seleziona il task corrente in base all'indice di avanzamento."""
        if not self.state.subtasks:
            self.state.current_task_index = 0
            return None

        if self.state.current_task_index < 0:
            self.state.current_task_index = 0

        if self.state.current_task_index >= len(self.state.subtasks):
            self.state.current_task_index = len(self.state.subtasks)
            return None

        task = self.state.subtasks[self.state.current_task_index]
        self.state.current_action = task
        return task

    def select_resource(self, task: str) -> str:
        """Seleziona una risorsa deterministica per il task."""
        if not task:
            raise ValueError("Task cannot be empty")

        resource = self.resource_selector.select(task)
        self.state.selected_resource = resource
        self.state.resource_history.append(
            {
                "task": task,
                "selected_resource": resource,
            }
        )
        return resource

    def retrieve_relevant_memory(self, task: str) -> list[str]:
        """Recupera memoria rilevante in modo deterministico tramite keyword matching."""
        if not task:
            return []

        matches = self.memory_store.retrieve(task)
        relevant = [entry.content for entry in matches]
        return relevant

    def _get_dependency_map(self) -> dict[str, list[str]]:
        """Return the local dependency metadata used by the current workflow."""
        return getattr(self, "_dependency_map", {})

    def _task_prerequisites(self, task: str) -> list[str]:
        """Return prerequisite tasks for the given task, if any."""
        dependency_map = self._get_dependency_map()
        prerequisites = dependency_map.get(task, [])
        if prerequisites is None:
            return []
        if isinstance(prerequisites, str):
            return [prerequisites]
        return [entry for entry in prerequisites if isinstance(entry, str)]

    def _task_has_status(self, task: str, status: str) -> bool:
        """Check whether a task has already been recorded in a terminal or intermediate status."""
        for entry in reversed(self.state.execution_history):
            if entry.get("task") != task:
                continue
            if entry.get("status") == status:
                return True
            verification = entry.get("verification")
            if isinstance(verification, dict) and verification.get("status") == status:
                return True
        for entry in reversed(self.state.verification_results):
            if entry.get("task") == task and entry.get("status") == status:
                return True
        return False

    def _task_is_terminal(self, task: str) -> bool:
        """Return True only for tasks that are past the execution gate."""
        return any(self._task_has_status(task, terminal) for terminal in ("passed", "failed", "blocked"))

    def _record_task_state(self, task: str, status: str, reason: str | None = None, **extra: object):
        """Persist a waiting/blocked state for a task without calling the provider."""
        for entry in self.state.execution_history:
            if entry.get("task") == task and entry.get("status") == status:
                return

        entry: dict[str, object] = {"task": task, "status": status}
        if reason is not None:
            entry["reason"] = reason
        entry.update(extra)
        self.state.execution_history.append(entry)

    def _dependency_state_for_task(self, task: str) -> tuple[str, str | None]:
        """Return the execution gate state for a task: executable, waiting, or blocked."""
        prerequisites = self._task_prerequisites(task)
        if not prerequisites:
            return "executable", None

        seen: set[str] = set()
        visiting: set[str] = set()

        def has_cycle(current: str) -> bool:
            if current in visiting:
                return True
            if current in seen:
                return False
            visiting.add(current)
            for prerequisite in self._task_prerequisites(current):
                if prerequisite not in self.state.subtasks:
                    continue
                if has_cycle(prerequisite):
                    return True
            visiting.remove(current)
            seen.add(current)
            return False

        if has_cycle(task):
            return "blocked", "circular_dependency"

        for prerequisite in prerequisites:
            if prerequisite not in self.state.subtasks:
                return "blocked", "missing_dependency"

            if self._task_has_status(prerequisite, "failed"):
                return "blocked", "failed_prerequisite"
            if self._task_has_status(prerequisite, "blocked"):
                return "blocked", "blocked_prerequisite"

            if self._task_has_status(prerequisite, "passed"):
                continue

            return "waiting", "pending_prerequisite"

        return "executable", None

    def execute_task(self, task: str, memory_context: list[str] | None = None) -> str:
        """Esegue un task e restituisce il risultato deterministico del provider."""
        if not task:
            raise ValueError("Task cannot be empty")

        resolved_memory_context = (
            list(memory_context) if memory_context is not None else self.retrieve_relevant_memory(task)
        )
        prompt = self._build_task_prompt(task, resolved_memory_context)
        result = self.model_provider.generate(prompt)
        self.state.current_action = task
        self.state.memory.append(
            {
                "type": "task_execution",
                "task": task,
                "prompt": prompt,
                "result": result,
                "relevant_memory": resolved_memory_context,
            }
        )
        return result

    def verify_task_result(self, task: str, result: str) -> dict[str, Any]:
        """Verifica che il risultato sia presente e non vuoto."""
        valid = bool(result and result.strip())
        verification = {
            "task": task,
            "status": "passed" if valid else "failed",
            "valid": valid,
            "result": result,
        }
        self.state.verification_results.append(verification)
        return verification

    def run_execution_loop(self, user_input: str, goal: str | None = None):
        """Esegue un loop esplicito di decomposizione, selezione, esecuzione e verifica."""
        self.receive(user_input)
        if goal is not None:
            self.set_goal(goal)

        self.decomposer.decompose(self.state)

        if not self.state.subtasks:
            self.state.final_answer = "No subtasks generated."
            self.state.status = "completed"
            return self.state

        if not self._get_dependency_map():
            while self.state.current_task_index < len(self.state.subtasks):
                task = self.select_next_task()
                if task is None:
                    break

                resource = self.select_resource(task)
                memory_context = self.retrieve_relevant_memory(task)
                self.state.context = list(memory_context)
                result = self.execute_task(task, memory_context)
                verification = self.verify_task_result(task, result)
                self.state.execution_history.append(
                    {
                        "task": task,
                        "resource": resource,
                        "result": result,
                        "verification": verification,
                        "relevant_memory": memory_context,
                    }
                )

                if verification["status"] == "passed":
                    self.memory_store.store(
                        result,
                        source="task_result",
                        associated_task=task,
                    )

                self.state.current_task_index += 1

            if self.state.current_task_index >= len(self.state.subtasks):
                self.state.status = "completed"
                self.state.final_answer = "\n\n".join(
                    (
                        f"Task: {entry['task']}\nResult: {entry['result']}\nVerification: {entry['verification']['status']}"
                        for entry in self.state.execution_history
                    )
                ) or "No subtasks generated."
            return self.state

        while True:
            remaining = [
                task for task in self.state.subtasks if not self._task_is_terminal(task)
            ]
            if not remaining:
                break

            progress = False
            for task in list(self.state.subtasks):
                if self._task_is_terminal(task):
                    continue

                task_state, reason = self._dependency_state_for_task(task)
                if task_state == "waiting":
                    self._record_task_state(task, "waiting", reason)
                    continue
                if task_state == "blocked":
                    self._record_task_state(task, "blocked", reason)
                    progress = True
                    continue

                resource = self.select_resource(task)
                memory_context = self.retrieve_relevant_memory(task)
                self.state.context = list(memory_context)
                result = self.execute_task(task, memory_context)
                verification = self.verify_task_result(task, result)
                self.state.execution_history.append(
                    {
                        "task": task,
                        "resource": resource,
                        "result": result,
                        "verification": verification,
                        "relevant_memory": memory_context,
                    }
                )

                if verification["status"] == "passed":
                    self.memory_store.store(
                        result,
                        source="task_result",
                        associated_task=task,
                    )

                progress = True
                self.state.current_task_index = min(
                    self.state.current_task_index + 1,
                    len(self.state.subtasks),
                )
                break

            if not progress:
                unresolved = [
                    task for task in self.state.subtasks if not self._task_is_terminal(task)
                ]
                for task in unresolved:
                    self._record_task_state(task, "blocked", "unresolved_dependency")
                break

        self.state.current_task_index = len(self.state.subtasks)
        self.state.status = "completed"

        if self.state.execution_history:
            final_entries = []
            for entry in self.state.execution_history:
                if "verification" in entry:
                    final_entries.append(
                        f"Task: {entry['task']}\nResult: {entry['result']}\nVerification: {entry['verification']['status']}"
                    )
                elif entry.get("status") in {"blocked", "waiting"}:
                    final_entries.append(
                        f"Task: {entry['task']}\nStatus: {entry['status']}\nReason: {entry.get('reason', 'n/a')}"
                    )
            self.state.final_answer = "\n\n".join(final_entries) or "No subtasks generated."
        else:
            self.state.final_answer = "No subtasks generated."

        return self.state

    def process(self, user_input: str, goal: str | None = None):
        """Elabora un input completo e restituisce lo stato aggiornato."""
        self.receive(user_input)
        if goal is not None:
            self.set_goal(goal)

        self.decomposer.decompose(self.state)
        prompt = self._build_prompt()
        response = self.model_provider.generate(prompt)

        self.state.memory.append(
            {
                "type": "model_response",
                "prompt": prompt,
                "response": response,
            }
        )
        return self.complete(response)

    def complete(self, answer: str):
        """Conclude il compito e aggiorna lo stato."""
        self.state.final_answer = answer
        self.state.status = "completed"
        return self.state
