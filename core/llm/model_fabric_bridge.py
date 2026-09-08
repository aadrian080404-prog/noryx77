from __future__ import annotations

from typing import Any

from noryx7_runtime.model_fabric import ModelFabric, ModelRequest


class ModelFabricBridge:
    """
    Ponte sicuro tra LLMBackedAgent e ModelFabric.

    Il bridge concede al modello esclusivamente capacità generativa.
    Tools, autorizzazione, esecuzione e stato restano fuori dal modello.
    """

    def __init__(
        self,
        fabric: ModelFabric,
        *,
        runtime_id: str = "",
        execution_id: str = "",
    ) -> None:
        if not isinstance(fabric, ModelFabric):
            raise TypeError("fabric must be a ModelFabric")

        if not isinstance(runtime_id, str):
            raise TypeError("runtime_id must be a string")

        if not isinstance(execution_id, str):
            raise TypeError("execution_id must be a string")

        self._fabric = fabric
        self._runtime_id = runtime_id
        self._execution_id = execution_id

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required")

        request = ModelRequest(
            prompt=prompt,
            required_capabilities=frozenset({"text"}),
            preferred_capabilities=frozenset({
                "reasoning",
                "chat",
            }),
            min_models=1,
            max_models=1,
            tools=(),
            runtime_id=self._runtime_id,
            execution_id=self._execution_id,
        )

        result = self._fabric.execute(request)

        output = getattr(result, "output", None)

        if not isinstance(output, str):
            raise RuntimeError("model_fabric_non_text_output")

        output = output.strip()

        if not output:
            raise RuntimeError("model_fabric_empty_output")

        return output
