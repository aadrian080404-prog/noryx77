from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ModelSelection:
    name: str
    output: object


class ModelFabric:
    """Bounded, runtime-bound model selection/execution boundary."""

    MAX_MODELS = 128
    MAX_PROMPT_BYTES = 256 * 1024
    MAX_CAPABILITIES = 64

    def __init__(self, models: Iterable[object], *, runtime_id: str, binding_key: bytes):
        if not isinstance(runtime_id, str) or not runtime_id.strip() or len(runtime_id.encode()) > 256:
            raise ValueError("invalid_runtime_id")
        if not isinstance(binding_key, bytes) or len(binding_key) < 32 or len(binding_key) > 128:
            raise ValueError("invalid_binding_key")
        items = tuple(models)
        if not items or len(items) > self.MAX_MODELS:
            raise ValueError("invalid_model_collection")
        names = set()
        for model in items:
            name = getattr(model, "name", None)
            capabilities = getattr(model, "capabilities", None)
            if not isinstance(name, str) or not name.strip() or name in names:
                raise ValueError("invalid_model_identity")
            if not isinstance(capabilities, (set, frozenset, tuple)):
                raise ValueError("invalid_model_capabilities")
            if len(capabilities) > self.MAX_CAPABILITIES or any(not isinstance(c, str) or not c.strip() for c in capabilities):
                raise ValueError("invalid_model_capabilities")
            if not callable(getattr(model, "generate", None)):
                raise ValueError("model_missing_generate")
            names.add(name)
        self._models = items
        self.runtime_id = runtime_id
        self._binding_key = bytes(binding_key)

    def generate(self, prompt: str, *, required_capabilities=(), tools=()) -> ModelSelection:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode()) > self.MAX_PROMPT_BYTES:
            raise ValueError("invalid_prompt")
        required = tuple(required_capabilities)
        if any(not isinstance(c, str) or not c.strip() for c in required):
            raise ValueError("invalid_required_capabilities")
        candidates = [m for m in self._models if set(required).issubset(set(getattr(m, "capabilities", ())))]
        if not candidates:
            raise LookupError("no_model_matches_capabilities")
        # Deterministic ranking: capability fit, then declared latency/cost, then name.
        model = min(candidates, key=lambda m: (float(getattr(m, "expected_latency_ms", 0.0)), float(getattr(m, "cost_per_call", 0.0)), m.name))
        output = model.generate(prompt, tools=tuple(tools))
        return ModelSelection(model.name, output)
