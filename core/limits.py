from dataclasses import dataclass

@dataclass(frozen=True)
class RuntimeLimits:
    max_input_chars: int = 100_000
    max_output_items: int = 1_000
    max_memory_items: int = 10_000
    max_actions_per_task: int = 32
    max_tool_calls_per_task: int = 16
    max_task_seconds: float = 30.0

    def validate_input(self, value: object) -> bool:
        return len(str(value)) <= self.max_input_chars
