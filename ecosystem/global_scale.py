"""Bounded primitives for globally distributed NORYX7 operation.

These objects model control-plane decisions and trust boundaries; they do not
pretend to be a cloud provider, database, scheduler, or network fabric.
Production adapters must supply those external implementations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from threading import RLock
from time import monotonic
from typing import Callable, Generic, TypeVar


MAX_ID_BYTES = 256
MAX_REGIONS = 4096
MAX_CELLS_PER_REGION = 65536
MAX_QUEUE_ITEMS = 1_000_000
MAX_EVENTS_PER_METRIC = 4096
MAX_SCENARIOS = 1_000_000


class Health(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    OFFLINE = "offline"


class DegradationMode(str, Enum):
    FULL = "full"
    REDUCED = "reduced"
    LIGHT = "light"
    QUEUE = "queue"
    RECOVERY = "recovery"


class WorkClass(str, Enum):
    REALTIME = "realtime"
    ASYNC = "async"


@dataclass(frozen=True)
class Capacity:
    cpu: int
    gpu: int
    memory: int
    bandwidth: int

    def __post_init__(self) -> None:
        if any(not isinstance(v, int) or v < 0 for v in (self.cpu, self.gpu, self.memory, self.bandwidth)):
            raise ValueError("invalid_capacity")

    def fits(self, required: "Capacity") -> bool:
        return all(a >= b for a, b in zip((self.cpu, self.gpu, self.memory, self.bandwidth),
                                           (required.cpu, required.gpu, required.memory, required.bandwidth)))

    def subtract(self, required: "Capacity") -> "Capacity":
        if not self.fits(required):
            raise ValueError("insufficient_capacity")
        return Capacity(self.cpu-required.cpu, self.gpu-required.gpu,
                        self.memory-required.memory, self.bandwidth-required.bandwidth)

    def add(self, value: "Capacity") -> "Capacity":
        return Capacity(self.cpu+value.cpu, self.gpu+value.gpu,
                        self.memory+value.memory, self.bandwidth+value.bandwidth)


@dataclass(frozen=True)
class Region:
    region_id: str
    health: Health = Health.HEALTHY
    latency_ms: float = 0.0
    capacity: Capacity = field(default_factory=lambda: Capacity(0, 0, 0, 0))
    data_residency: str = "global"
    version: str = ""

    def __post_init__(self) -> None:
        _id(self.region_id)
        if self.latency_ms < 0 or self.latency_ms != self.latency_ms:
            raise ValueError("invalid_latency")
        _id(self.data_residency)


@dataclass(frozen=True)
class Cell:
    cell_id: str
    region_id: str
    health: Health = Health.HEALTHY
    capacity: Capacity = field(default_factory=lambda: Capacity(0, 0, 0, 0))
    version: str = ""

    def __post_init__(self) -> None:
        _id(self.cell_id)
        _id(self.region_id)


def _id(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > MAX_ID_BYTES:
        raise ValueError("invalid_identifier")
    return value


class GlobalControlPlane:
    """Thread-safe registry and health view; no user-task execution."""
    def __init__(self) -> None:
        self._regions: dict[str, Region] = {}
        self._lock = RLock()

    def register(self, region: Region) -> None:
        if not isinstance(region, Region):
            raise TypeError("region_required")
        with self._lock:
            if region.region_id not in self._regions and len(self._regions) >= MAX_REGIONS:
                raise MemoryError("region_capacity_exceeded")
            self._regions[region.region_id] = region

    def update(self, region: Region) -> None:
        self.register(region)

    def snapshot(self) -> tuple[Region, ...]:
        with self._lock:
            return tuple(self._regions.values())

    def select(self, *, residency: str = "global", required: Capacity = Capacity(0,0,0,0), excluded: frozenset[str] = frozenset()) -> Region:
        _id(residency)
        with self._lock:
            candidates = [r for r in self._regions.values()
                          if r.region_id not in excluded and r.health is Health.HEALTHY
                          and r.capacity.fits(required)
                          and (residency == "global" or r.data_residency == residency)]
            if not candidates:
                raise LookupError("no_healthy_region")
            return min(candidates, key=lambda r: (r.latency_ms, -r.capacity.gpu, r.region_id))


class CellRegistry:
    def __init__(self) -> None:
        self._cells: dict[str, Cell] = {}
        self._lock = RLock()

    def register(self, cell: Cell) -> None:
        if not isinstance(cell, Cell):
            raise TypeError("cell_required")
        with self._lock:
            if cell.cell_id not in self._cells and len(self._cells) >= MAX_CELLS_PER_REGION:
                raise MemoryError("cell_capacity_exceeded")
            self._cells[cell.cell_id] = cell

    def select(self, region_id: str, required: Capacity) -> Cell:
        _id(region_id)
        with self._lock:
            candidates = [c for c in self._cells.values() if c.region_id == region_id
                          and c.health is Health.HEALTHY and c.capacity.fits(required)]
            if not candidates:
                raise LookupError("no_healthy_cell")
            return max(candidates, key=lambda c: (c.capacity.gpu, c.capacity.cpu, c.cell_id))


@dataclass(frozen=True)
class WorkRequest:
    request_id: str
    required: Capacity
    work_class: WorkClass
    residency: str = "global"
    priority: int = 0
    model_tier: str = "small"
    user_priority: int = 0

    def __post_init__(self) -> None:
        _id(self.request_id); _id(self.residency); _id(self.model_tier)
        if not isinstance(self.required, Capacity) or not isinstance(self.work_class, WorkClass):
            raise TypeError("invalid_work_request")
        if not all(isinstance(v, int) and v >= 0 for v in (self.priority, self.user_priority)):
            raise ValueError("invalid_priority")


@dataclass(frozen=True)
class Route:
    region_id: str
    cell_id: str
    model_tier: str
    degradation: DegradationMode


class GlobalTrafficRouter:
    def __init__(self, control: GlobalControlPlane, cells: CellRegistry) -> None:
        self.control = control
        self.cells = cells

    def route(self, request: WorkRequest) -> Route:
        if not isinstance(request, WorkRequest):
            raise TypeError("work_request_required")
        region = self.control.select(residency=request.residency, required=request.required)
        try:
            cell = self.cells.select(region.region_id, request.required)
            mode = DegradationMode.FULL
        except LookupError:
            # A healthy region without a suitable cell is not silently treated
            # as capacity: queue/degrade is explicit and fail-closed.
            raise LookupError("no_routable_cell")
        return Route(region.region_id, cell.cell_id, request.model_tier, mode)


T = TypeVar("T")


class ElasticComputeFabric:
    """Accounting layer for replaceable workers; adapters perform real scaling."""
    def __init__(self) -> None:
        self._available: dict[str, Capacity] = {}
        self._lock = RLock()

    def register_worker_pool(self, pool_id: str, capacity: Capacity) -> None:
        _id(pool_id)
        if not isinstance(capacity, Capacity): raise TypeError("capacity_required")
        with self._lock: self._available[pool_id] = capacity

    def acquire(self, required: Capacity) -> str:
        with self._lock:
            candidates = [(pid, cap) for pid, cap in self._available.items() if cap.fits(required)]
            if not candidates: raise LookupError("compute_capacity_unavailable")
            pid, cap = min(candidates, key=lambda item: (item[1].gpu, item[1].cpu, item[0]))
            self._available[pid] = cap.subtract(required)
            return pid

    def release(self, pool_id: str, capacity: Capacity) -> None:
        _id(pool_id)
        with self._lock:
            if pool_id not in self._available: raise KeyError("unknown_worker_pool")
            self._available[pool_id] = self._available[pool_id].add(capacity)


@dataclass(frozen=True)
class QueuedWork(Generic[T]):
    sequence: int
    request: WorkRequest
    payload: T


class EventFabric(Generic[T]):
    """Bounded in-memory queue contract; durable brokers belong behind adapters."""
    def __init__(self, max_items: int = MAX_QUEUE_ITEMS) -> None:
        if not isinstance(max_items, int) or not 1 <= max_items <= MAX_QUEUE_ITEMS:
            raise ValueError("invalid_queue_limit")
        self._max = max_items; self._seq = 0; self._items: list[QueuedWork[T]] = []; self._lock = RLock()

    def publish(self, request: WorkRequest, payload: T) -> int:
        if not isinstance(request, WorkRequest): raise TypeError("work_request_required")
        with self._lock:
            if len(self._items) >= self._max: raise MemoryError("queue_capacity_exceeded")
            self._seq += 1; self._items.append(QueuedWork(self._seq, request, payload)); return self._seq

    def drain(self, limit: int) -> tuple[QueuedWork[T], ...]:
        if not isinstance(limit, int) or limit < 1: raise ValueError("invalid_drain_limit")
        with self._lock:
            ordered = sorted(self._items, key=lambda x: (-x.request.priority, x.sequence))[:limit]
            selected = {x.sequence for x in ordered}
            self._items = [x for x in self._items if x.sequence not in selected]
            return tuple(ordered)

    def __len__(self) -> int:
        with self._lock: return len(self._items)


@dataclass(frozen=True)
class LanguageContext:
    input_language: str
    output_language: str
    source_languages: tuple[str, ...] = ()
    locale: str = ""
    timezone: str = "UTC"
    unit_system: str = "metric"
    cultural_context: str = ""

    def __post_init__(self) -> None:
        for value in (self.input_language, self.output_language, self.locale, self.timezone, self.unit_system, self.cultural_context):
            if not isinstance(value, str) or len(value.encode()) > MAX_ID_BYTES: raise ValueError("invalid_language_context")
        if not isinstance(self.source_languages, tuple) or any(not isinstance(x, str) for x in self.source_languages):
            raise TypeError("invalid_source_languages")


@dataclass(frozen=True)
class SemanticEnvelope:
    semantic_digest: str
    original_language: str
    context: LanguageContext


class LanguageFabric:
    """Language normalization contract; semantic reasoning remains language-neutral."""
    def normalize(self, text: str, context: LanguageContext) -> SemanticEnvelope:
        if not isinstance(text, str) or not text.strip(): raise ValueError("text_required")
        if not isinstance(context, LanguageContext): raise TypeError("language_context_required")
        digest = sha256((context.input_language + "\0" + text).encode("utf-8")).hexdigest()
        return SemanticEnvelope(digest, context.input_language, context)


@dataclass(frozen=True)
class ResourceBudget:
    tokens: int
    cpu_ms: int
    gpu_ms: int
    memory_bytes: int
    tool_calls: int
    bandwidth_bytes: int

    def __post_init__(self) -> None:
        if any(not isinstance(v, int) or v < 0 for v in (self.tokens, self.cpu_ms, self.gpu_ms, self.memory_bytes, self.tool_calls, self.bandwidth_bytes)):
            raise ValueError("invalid_resource_budget")


class ResourceController:
    def admit(self, budget: ResourceBudget, *, used: ResourceBudget = ResourceBudget(0,0,0,0,0,0)) -> None:
        if not isinstance(budget, ResourceBudget) or not isinstance(used, ResourceBudget): raise TypeError("resource_budget_required")
        if any(a > b for a, b in zip((used.tokens,used.cpu_ms,used.gpu_ms,used.memory_bytes,used.tool_calls,used.bandwidth_bytes),
                                     (budget.tokens,budget.cpu_ms,budget.gpu_ms,budget.memory_bytes,budget.tool_calls,budget.bandwidth_bytes))):
            raise PermissionError("resource_budget_exceeded")


class DegradationController:
    def __init__(self) -> None:
        self._mode = DegradationMode.FULL; self._lock = RLock()

    @property
    def mode(self) -> DegradationMode:
        with self._lock: return self._mode

    def set_mode(self, mode: DegradationMode) -> None:
        if not isinstance(mode, DegradationMode): raise TypeError("invalid_degradation_mode")
        with self._lock: self._mode = mode

    def require_available(self, work_class: WorkClass) -> DegradationMode:
        if not isinstance(work_class, WorkClass): raise TypeError("work_class_required")
        mode = self.mode
        if mode is DegradationMode.RECOVERY: raise PermissionError("recovery_mode_denies_execution")
        if work_class is WorkClass.REALTIME and mode is DegradationMode.QUEUE:
            raise PermissionError("realtime_capacity_unavailable")
        return mode


@dataclass(frozen=True)
class MetricEvent:
    name: str
    value: float
    timestamp: float
    region_id: str = ""
    cell_id: str = ""


class ObservabilityFabric:
    """Bounded metrics only; callers must not place raw user content in events."""
    def __init__(self, max_events_per_metric: int = MAX_EVENTS_PER_METRIC) -> None:
        if not 1 <= max_events_per_metric <= MAX_EVENTS_PER_METRIC: raise ValueError("invalid_observability_limit")
        self._max = max_events_per_metric; self._events: dict[str, list[MetricEvent]] = {}; self._lock = RLock()

    def record(self, name: str, value: float, *, region_id: str = "", cell_id: str = "") -> None:
        _id(name); _id(region_id or "global"); _id(cell_id or "global")
        if not isinstance(value, (int, float)) or value != value: raise ValueError("invalid_metric_value")
        event = MetricEvent(name, float(value), monotonic(), region_id, cell_id)
        with self._lock:
            bucket = self._events.setdefault(name, [])
            bucket.append(event)
            if len(bucket) > self._max: del bucket[:-self._max]

    def snapshot(self, name: str) -> tuple[MetricEvent, ...]:
        _id(name)
        with self._lock: return tuple(self._events.get(name, ()))


@dataclass(frozen=True)
class RecoveryTarget:
    region_id: str
    version: str
    required_capacity: Capacity


class DisasterRecoveryPlan:
    def choose(self, regions: tuple[Region, ...], failed_region_id: str, required: Capacity) -> Region:
        _id(failed_region_id)
        candidates = [r for r in regions if r.region_id != failed_region_id and r.health is Health.HEALTHY and r.capacity.fits(required)]
        if not candidates: raise LookupError("no_disaster_recovery_target")
        return min(candidates, key=lambda r: (r.latency_ms, r.region_id))


class SelfHealingController:
    """Only advances through explicit proposal/verification/deployment states."""
    _ORDER = ("detected", "diagnosed", "proposed", "sandboxed", "verified", "canary", "deployed")
    def __init__(self) -> None:
        self._stage: dict[str, str] = {}; self._lock = RLock()

    def advance(self, component_id: str, stage: str) -> None:
        _id(component_id); _id(stage)
        if stage not in self._ORDER: raise ValueError("invalid_healing_stage")
        with self._lock:
            current = self._stage.get(component_id)
            if current is not None and self._ORDER.index(stage) != self._ORDER.index(current) + 1:
                raise PermissionError("invalid_healing_transition")
            self._stage[component_id] = stage

    def rollback(self, component_id: str) -> None:
        _id(component_id)
        with self._lock: self._stage.pop(component_id, None)

    def stage(self, component_id: str) -> str | None:
        with self._lock: return self._stage.get(component_id)


@dataclass(frozen=True)
class SyntheticScenario:
    scenario_id: str
    request: WorkRequest
    failure_mode: str = "none"
    language: str = "en"
    network_ms: int = 0

    def __post_init__(self) -> None:
        _id(self.scenario_id); _id(self.failure_mode); _id(self.language)
        if not isinstance(self.network_ms, int) or self.network_ms < 0: raise ValueError("invalid_network_delay")


class SyntheticTestingGrid:
    def __init__(self, max_scenarios: int = MAX_SCENARIOS) -> None:
        if not 1 <= max_scenarios <= MAX_SCENARIOS: raise ValueError("invalid_scenario_limit")
        self.max_scenarios = max_scenarios

    def generate(self, seed: int, count: int) -> tuple[SyntheticScenario, ...]:
        if not isinstance(seed, int) or not isinstance(count, int) or count < 0 or count > self.max_scenarios:
            raise ValueError("invalid_scenario_request")
        scenarios = []
        for index in range(count):
            digest = sha256(f"{seed}:{index}".encode()).hexdigest()
            work_class = WorkClass.REALTIME if int(digest[0], 16) % 2 == 0 else WorkClass.ASYNC
            failure = ("none", "network", "worker", "memory", "region")[int(digest[1], 16) % 5]
            request = WorkRequest(digest[:32], Capacity(1, int(digest[2],16)%4, 1, 1), work_class, priority=int(digest[3],16)%10)
            scenarios.append(SyntheticScenario(digest, request, failure_mode=failure, language=("en","it","de","ja","es")[int(digest[4],16)%5], network_ms=int(digest[5:9],16)%5000))
        return tuple(scenarios)
