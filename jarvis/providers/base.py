from typing import Protocol

class ModelProvider(Protocol):
    def generate(self, prompt: str) -> str: ...
