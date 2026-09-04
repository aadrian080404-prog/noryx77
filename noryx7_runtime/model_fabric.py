from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence


class ModelAdapter(Protocol):
    name: str
    capabilities: frozenset[str]
    cost_per_call: float
    expected_latency_ms: float
    def generate(self, prompt: str, *, tools: Sequence[str] = ()) -> Any: ...


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


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
    runtime_id: str = ""
    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip(): raise ValueError("prompt is required")
        if not isinstance(self.required_capabilities, frozenset) or any(not isinstance(item, str) or not item for item in self.required_capabilities): raise ValueError("invalid required capabilities")
        if not isinstance(self.preferred_capabilities, frozenset) or any(not isinstance(item, str) or not item for item in self.preferred_capabilities): raise ValueError("invalid preferred capabilities")
        if not isinstance(self.tools, tuple) or any(not isinstance(item, str) or not item for item in self.tools): raise ValueError("invalid model tools")
        if isinstance(self.min_models, bool) or isinstance(self.max_models, bool) or not isinstance(self.min_models, int) or not isinstance(self.max_models, int) or self.min_models < 1 or self.max_models < self.min_models: raise ValueError("invalid model fan-out")
        if self.max_cost is not None and (isinstance(self.max_cost, bool) or not isinstance(self.max_cost, (int, float)) or not math.isfinite(self.max_cost) or self.max_cost < 0): raise ValueError("max_cost must be a finite non-negative number")
        if self.max_latency_ms is not None and (isinstance(self.max_latency_ms, bool) or not isinstance(self.max_latency_ms, (int, float)) or not math.isfinite(self.max_latency_ms) or self.max_latency_ms <= 0): raise ValueError("max_latency_ms must be a finite positive number")
        if not isinstance(self.runtime_id, str): raise ValueError("runtime_id must be a string")

@dataclass(frozen=True)
class ModelCandidate:
    name: str
    output: Any
    latency_ms: float
    cost: float
    output_digest: str = ""

@dataclass(frozen=True)
class FabricResult:
    output: Any
    candidates: tuple[ModelCandidate, ...]
    selected_model: str
    confidence: float
    degraded: bool = False
    runtime_id: str = ""
    request_digest: str = ""
    result_mac: str = ""

Verifier = Callable[[str, Any], float]
Synthesizer = Callable[[Sequence[ModelCandidate]], Any]

class ModelFabric:
    """Provider-neutral intelligence layer with runtime-bound provenance."""
    def __init__(self, models: Sequence[ModelAdapter], *, runtime_id: str | None = None, binding_key: bytes | None = None) -> None:
        if not models: raise ValueError("at least one model is required")
        if runtime_id is not None and (not isinstance(runtime_id, str) or not runtime_id): raise ValueError("runtime_id must be a non-empty string")
        if binding_key is not None and (not isinstance(binding_key, bytes) or len(binding_key) < 32): raise ValueError("binding_key must be at least 32 bytes")
        if binding_key is not None and runtime_id is None: raise ValueError("runtime_id is required for bound model fabric")
        names: set[str] = set(); validated: list[ModelAdapter] = []
        for model in models:
            name = getattr(model, "name", None); caps = getattr(model, "capabilities", None)
            if not isinstance(name, str) or not name or name in names: raise ValueError("model names must be unique and non-empty")
            if not isinstance(caps, frozenset): raise TypeError("model capabilities must be frozenset")
            if any(not isinstance(item, str) or not item for item in caps): raise ValueError("model capabilities must contain non-empty strings")
            if not callable(getattr(model, "generate", None)): raise TypeError("model must expose generate")
            if isinstance(model.cost_per_call, bool) or not isinstance(model.cost_per_call, (int, float)) or not math.isfinite(model.cost_per_call) or model.cost_per_call < 0: raise ValueError("invalid model economics")
            if isinstance(model.expected_latency_ms, bool) or not isinstance(model.expected_latency_ms, (int, float)) or not math.isfinite(model.expected_latency_ms) or model.expected_latency_ms <= 0: raise ValueError("invalid model economics")
            names.add(name); validated.append(model)
        self._models = tuple(validated); self._runtime_id = runtime_id; self._binding_key = binding_key
    @property
    def runtime_id(self) -> str | None: return self._runtime_id
    def _rank(self, request: ModelRequest) -> tuple[ModelAdapter, ...]:
        if self._runtime_id is not None and request.runtime_id != self._runtime_id: raise PermissionError("model request runtime identity mismatch")
        required = frozenset(request.required_capabilities); preferred = frozenset(request.preferred_capabilities)
        latency_limit = None if request.max_latency_ms == 0 else request.max_latency_ms
        eligible = [m for m in self._models if required.issubset(m.capabilities) and (request.max_cost is None or m.cost_per_call <= request.max_cost) and (latency_limit is None or m.expected_latency_ms <= latency_limit)]
        eligible.sort(key=lambda m: (-len(preferred.intersection(m.capabilities)), m.expected_latency_ms, m.cost_per_call, m.name))
        if len(eligible) < request.min_models: raise RuntimeError("insufficient model coverage for request")
        return tuple(eligible[:request.max_models])
    def route(self, request: ModelRequest) -> tuple[str, ...]: return tuple(model.name for model in self._rank(request))
    def _request_digest(self, request: ModelRequest) -> str:
        return _digest({"prompt": request.prompt, "required_capabilities": sorted(request.required_capabilities), "preferred_capabilities": sorted(request.preferred_capabilities), "max_cost": request.max_cost, "max_latency_ms": request.max_latency_ms, "min_models": request.min_models, "max_models": request.max_models, "tools": list(request.tools), "runtime_id": request.runtime_id})
    def request_digest(self, request: ModelRequest) -> str:
        """Return the canonical digest used to bind a request to its fabric execution."""
        if not isinstance(request, ModelRequest): raise TypeError("invalid_model_request")
        return self._request_digest(request)
    @staticmethod
    def _result_envelope_digest(output: Any, candidates: Sequence[ModelCandidate], selected_model: str, request_digest: str) -> str:
        return _digest({"output": output, "candidates": tuple((c.name, c.output_digest, c.latency_ms, c.cost) for c in candidates), "selected_model": selected_model, "request_digest": request_digest})
    def result_digest(self, request: ModelRequest, result: FabricResult) -> str:
        """Return the verified, deterministic result-envelope digest."""
        if not self.verify_result(request, result): raise ValueError("invalid_fabric_result")
        return self._result_envelope_digest(result.output, result.candidates, result.selected_model, result.request_digest)
    def _result_mac(self, request_digest: str, output_digest: str, selected_model: str) -> str:
        if self._binding_key is None: return output_digest
        payload = f"{self._runtime_id or ''}:{request_digest}:{output_digest}:{selected_model}".encode("utf-8")
        return hmac.new(self._binding_key, payload, hashlib.sha256).hexdigest()
    def verify_result(self, request: ModelRequest, result: FabricResult) -> bool:
        if not isinstance(request, ModelRequest) or not isinstance(result, FabricResult): return False
        if self._runtime_id is not None and result.runtime_id != self._runtime_id: return False
        if not isinstance(result.selected_model, str) or not result.selected_model.strip(): return False
        if isinstance(result.confidence, bool) or not isinstance(result.confidence, (int, float)) or not math.isfinite(result.confidence) or not 0 <= result.confidence <= 1: return False
        if not isinstance(result.degraded, bool) or not isinstance(result.runtime_id, str) or not isinstance(result.request_digest, str) or not isinstance(result.result_mac, str): return False
        if len(result.candidates) < 1 or len(result.candidates) > len(self._models): return False
        expected_request_digest = self._request_digest(request)
        if result.request_digest != expected_request_digest or not result.candidates: return False
        names: set[str] = set()
        for candidate in result.candidates:
            if not isinstance(candidate, ModelCandidate) or not isinstance(candidate.name, str) or not candidate.name or candidate.name in names: return False
            if isinstance(candidate.latency_ms, bool) or not isinstance(candidate.latency_ms, (int, float)) or not math.isfinite(candidate.latency_ms) or candidate.latency_ms < 0: return False
            if isinstance(candidate.cost, bool) or not isinstance(candidate.cost, (int, float)) or not math.isfinite(candidate.cost) or candidate.cost < 0: return False
            if not isinstance(candidate.output_digest, str) or len(candidate.output_digest) != 64 or any(ch not in "0123456789abcdef" for ch in candidate.output_digest): return False
            try:
                if _digest(candidate.output) != candidate.output_digest: return False
            except (TypeError, ValueError, OverflowError): return False
            names.add(candidate.name)
        if result.selected_model not in names: return False
        try:
            expected_envelope_digest = self._result_envelope_digest(result.output, result.candidates, result.selected_model, result.request_digest)
        except (TypeError, ValueError, OverflowError):
            return False
        if self._binding_key is None:
            return hmac.compare_digest(result.result_mac, expected_envelope_digest)
        expected_mac = self._result_mac(result.request_digest, expected_envelope_digest, result.selected_model)
        return hmac.compare_digest(result.result_mac, expected_mac)
    def execute(self, request: ModelRequest, *, verifier: Verifier | None = None, synthesizer: Synthesizer | None = None) -> FabricResult:
        selected = self._rank(request); candidates: list[ModelCandidate] = []
        for model in selected:
            try:
                import time
                started = time.monotonic(); output = model.generate(request.prompt, tools=request.tools)
                candidates.append(ModelCandidate(model.name, output, (time.monotonic() - started) * 1000.0, model.cost_per_call, _digest(output)))
            except Exception: continue
        candidates.sort(key=lambda candidate: candidate.name)
        if len(candidates) < request.min_models: raise RuntimeError("model ensemble could not satisfy minimum quorum")
        if verifier is not None:
            scored = sorted(((max(0.0, min(1.0, float(verifier(c.name, c.output)))), c) for c in candidates), key=lambda x: (-x[0], x[1].name)); confidence, winner = scored[0]; output = winner.output if synthesizer is None else synthesizer(tuple(c for _, c in scored)); selected_model = winner.name
        elif synthesizer is not None:
            output = synthesizer(tuple(candidates)); selected_model, confidence = candidates[0].name, 0.0
        else: output, selected_model, confidence = candidates[0].output, candidates[0].name, 0.0
        request_digest = self._request_digest(request); output_digest = self._result_envelope_digest(output, candidates, selected_model, request_digest)
        result = FabricResult(output, tuple(candidates), selected_model, confidence, len(candidates) < len(selected), request.runtime_id, request_digest, self._result_mac(request_digest, output_digest, selected_model))
        if not self.verify_result(request, result): raise RuntimeError("model_result_integrity_failure")
        return result
