from dataclasses import dataclass, field
from typing import Any


@dataclass
class NORYXState:
    """
    Stato interno di NORYX7 durante l'esecuzione di un'attività.
    """

    user_input: str = ""

    context: list[str] = field(default_factory=list)

    goal: str = ""

    subtasks: list[str] = field(default_factory=list)

    current_task_index: int = 0

    execution_history: list[dict[str, Any]] = field(default_factory=list)

    memory: list[dict[str, Any]] = field(default_factory=list)

    available_tools: list[str] = field(default_factory=list)

    selected_models: list[str] = field(default_factory=list)

    hypotheses: list[str] = field(default_factory=list)

    verification_results: list[dict[str, Any]] = field(default_factory=list)

    confidence: float = 0.0

    current_action: str = ""

    selected_resource: str = ""

    resource_history: list[dict[str, Any]] = field(default_factory=list)

    final_answer: str = ""

    status: str = "initialized"
