from __future__ import annotations

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Abstract interface for all model providers in NORYX7."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return a model response for the supplied prompt."""
        raise NotImplementedError


class MockModelProvider(ModelProvider):
    """Simple deterministic provider used for tests and local orchestration."""

    def __init__(self, response: str | None = None):
        self.response = response if response is not None else "Mock model response"

    def generate(self, prompt: str) -> str:
        if not self.response:
            return ""
        return f"{self.response} :: prompt={prompt}"
