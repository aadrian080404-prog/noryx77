from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RuntimeLimits:
    max_input_chars: int = 100_000
    max_output_chars: int = 100_000
    max_output_items: int = 1_000
    max_memory_items: int = 10_000
    max_actions_per_task: int = 32
    max_tool_calls_per_task: int = 16
    max_task_seconds: float = 30.0

    def __post_init__(self):
        numeric = {
            "max_input_chars": self.max_input_chars,
            "max_output_chars": self.max_output_chars,
            "max_output_items": self.max_output_items,
            "max_memory_items": self.max_memory_items,
            "max_actions_per_task": self.max_actions_per_task,
            "max_tool_calls_per_task": self.max_tool_calls_per_task,
        }
        for name, value in numeric.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"invalid_runtime_limit:{name}")
        if (
            isinstance(self.max_task_seconds, bool)
            or not isinstance(self.max_task_seconds, (int, float))
            or not math.isfinite(self.max_task_seconds)
            or self.max_task_seconds <= 0
        ):
            raise ValueError("invalid_runtime_limit:max_task_seconds")

    def validate_input(self, value: object) -> bool:
        return len(str(value)) <= self.max_input_chars

    def validate_output(self, value: object) -> bool:
        return value is not None and len(str(value)) <= self.max_output_chars

    def validate_output_items(self, value: object) -> bool:
        if isinstance(value, (list, tuple, set, frozenset, dict)):
            return len(value) <= self.max_output_items
        return True

    def validate_count(self, value: int, maximum: int) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum
