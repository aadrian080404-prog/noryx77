from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence


class ModelAdapter(Protocol):
    name: str
    capabilities: frozenset[str]
    cost_per_call: float
    expected_latency_ms: float

    def generate(self, prompt: str, *, tools: Sequence[str] = ()) -> Any: ...


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    required_capabilities: frozenset[str] = frozenset()
    preferred_capabilities: frozenset[str] = frozenset()
    max_cost: float | None = None
    max_latency_ms: float | None = None
    min_models: int = 1
    max_models: int = 3
    tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("prompt is required")
        if self.min_models < 1 or self.max_models < self.min_models:
            raise ValueError("invalid model fan-out")
        if self.max_cost is not None and self.max_cost < 0:
            raise ValueError("max_cost must be non-negative")
        if self.max_latency_ms is not None and self.max_latency_ms <= 0:
            raise ValueError("max_latency_ms must be positive")


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    output: Any
    latency_ms: float
    cost: float


@dataclass(frozen=True)
class FabricResult:
    output: Any
    candidates: tuple[ModelCandidate, ...]
    selected_model: str
    confidence: float
    degraded: bool = False


Verifier = Callable[[str, Any], float]
Synthesizer = Callable[[Sequence[ModelCandidate]], Any]


class ModelFabric:
    """Provider-neutral intelligence layer for routing, diversity and verification."""

    def __init__(self, models: Sequence[ModelAdapter]) -> None:
        if not models:
            raise ValueError("at least one model is required")
        names: set[str] = set()
        validated: list[ModelAdapter] = []
        for model in models:
            name = getattr(model, "name", None)
            caps = getattr(model, "capabilities", None)
            if not isinstance(name, str) or not name or name in names:
                raise ValueError("model names must be unique and non-empty")
            if not isinstance(caps, frozenset):
                raise TypeError("model capabilities must be frozenset")
            if any(not isinstance(item, str) or not item for item in caps):
                raise ValueError("model capabilities must contain non-empty strings")
            if not callable(getattr(model, "generate", None)):
                raise TypeError("model must expose generate")
            if model.cost_per_call < 0 or model.expected_latency_ms <= 0:
                raise ValueError("invalid model economics")
            names.add(name)
            validated.append(model)
        self._models = tuple(validated)

    def _rank(self, request: ModelRequest) -> tuple[ModelAdapter, ...]:
        eligible = [
            model for model in self._models
            if request.required_capabilities.issubset(model.capabilities)
            and (request.max_cost is None or model.cost_per_call <= request.max_cost)
            and (request.max_latency_ms is None or model.expected_latency_ms <= request.max_latency_ms)
        ]
        eligible.sort(key=lambda m: (
            -len(request.preferred_capabilities.intersection(m.capabilities)),
            m.expected_latency_ms,
            m.cost_per_call,
            m.name,
        ))
        if len(eligible) < request.min_models:
            raise RuntimeError("insufficient model coverage for request")
        return tuple(eligible[:request.max_models])

    def route(self, request: ModelRequest) -> tuple[str, ...]:
        return tuple(model.name for model in self._rank(request))

    def execute(self, request: ModelRequest, *, verifier: Verifier | None = None, synthesizer: Synthesizer | None = None) -> FabricResult:
        selected = self._rank(request)
        candidates: list[ModelCandidate] = []
        for model in selected:
            try:
                import time
                started = time.monotonic()
                output = model.generate(request.prompt, tools=request.tools)
                candidates.append(ModelCandidate(model.name, output, (time.monotonic() - started) * 1000.0, model.cost_per_call))
            except Exception:
                continue
        candidates.sort(key=lambda candidate: candidate.name)
        if len(candidates) < request.min_models:
            raise RuntimeError("model ensemble could not satisfy minimum quorum")
        if verifier is not None:
            scored = sorted(((max(0.0, min(1.0, float(verifier(c.name, c.output)))), c) for c in candidates), key=lambda x: (-x[0], x[1].name))
            confidence, winner = scored[0]
            output = winner.output if synthesizer is None else synthesizer(tuple(c for _, c in scored))
            selected_model = winner.name
        elif synthesizer is not None:
            output = synthesizer(tuple(candidates))
            selected_model, confidence = candidates[0].name, 0.0
        else:
            output, selected_model, confidence = candidates[0].output, candidates[0].name, 0.0
        return FabricResult(output, tuple(candidates), selected_model, confidence, len(candidates) < len(selected))
