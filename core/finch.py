"""Bounded event-fusion and forecasting primitives inspired by fictional Machine-style architectures.

This module is intentionally defensive: it observes only events explicitly supplied by
trusted adapters, computes relevance/anomaly scores, and produces bounded hypotheses.
It does not identify people, bypass permissions, or perform surveillance by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence


MAX_ID = 256
MAX_TEXT = 4096
MAX_EVENTS = 4096
MAX_NEIGHBORS = 32


def _text(value: str, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid_text")
    if len(value.encode("utf-8")) > limit:
        raise ValueError("text_size_exceeded")
    return value


@dataclass(frozen=True)
class Observation:
    observation_id: str
    timestamp: float
    source: str
    subject: str
    signal: str
    severity: float = 0.0

    def __post_init__(self) -> None:
        _text(self.observation_id, MAX_ID)
        _text(self.source, MAX_ID)
        _text(self.subject, MAX_ID)
        _text(self.signal)
        if isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)) or not math.isfinite(self.timestamp):
            raise ValueError("invalid_timestamp")
        if isinstance(self.severity, bool) or not isinstance(self.severity, (int, float)) or not math.isfinite(self.severity) or not 0.0 <= self.severity <= 1.0:
            raise ValueError("invalid_severity")


@dataclass(frozen=True)
class Relevance:
    observation_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Anomaly:
    observation_id: str
    score: float
    reason: str


@dataclass(frozen=True)
class Forecast:
    subject: str
    likelihood: float
    horizon: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class GraphSnapshot:
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    digest: str


class EventGraph:
    """Small temporal relationship graph with deterministic canonicalization."""

    def __init__(self, *, max_events: int = MAX_EVENTS, max_neighbors: int = MAX_NEIGHBORS):
        if not isinstance(max_events, int) or isinstance(max_events, bool) or max_events <= 0 or max_events > MAX_EVENTS:
            raise ValueError("invalid_max_events")
        if not isinstance(max_neighbors, int) or isinstance(max_neighbors, bool) or max_neighbors <= 0 or max_neighbors > MAX_NEIGHBORS:
            raise ValueError("invalid_max_neighbors")
        self._max_events = max_events
        self._max_neighbors = max_neighbors
        self._observations: list[Observation] = []
        self._edges: set[tuple[str, str]] = set()

    def add(self, observation: Observation, *, related_to: Sequence[str] = ()) -> None:
        if not isinstance(observation, Observation):
            raise TypeError("observation_required")
        if len(self._observations) >= self._max_events:
            raise OverflowError("event_graph_capacity")
        related = tuple(dict.fromkeys(related_to))
        if len(related) > self._max_neighbors:
            raise ValueError("too_many_related_nodes")
        self._observations.append(observation)
        for node in related:
            _text(node, MAX_ID)
            self._edges.add((observation.observation_id, node))

    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    def snapshot(self) -> GraphSnapshot:
        nodes = tuple(sorted({o.observation_id for o in self._observations} | {b for _, b in self._edges}))
        edges = tuple(sorted(self._edges))
        payload = json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return GraphSnapshot(nodes, edges, hashlib.sha256(payload).hexdigest())


class MachineInspiredAnalyzer:
    """Defensive event-fusion engine: relevance -> anomaly -> bounded forecast."""

    def __init__(self, *, anomaly_baseline: float = 0.5):
        if isinstance(anomaly_baseline, bool) or not isinstance(anomaly_baseline, (int, float)) or not math.isfinite(anomaly_baseline) or not 0.0 <= anomaly_baseline <= 1.0:
            raise ValueError("invalid_anomaly_baseline")
        self._baseline = float(anomaly_baseline)

    @staticmethod
    def rank_relevance(observations: Sequence[Observation], *, keywords: Sequence[str] = ()) -> tuple[Relevance, ...]:
        terms = tuple(_text(k, MAX_ID).casefold() for k in keywords)
        ranked = []
        for item in observations:
            haystack = f"{item.source} {item.subject} {item.signal}".casefold()
            matches = tuple(term for term in terms if term in haystack)
            score = min(1.0, 0.7 * item.severity + 0.3 * (len(matches) / max(1, len(terms)))) if terms else item.severity
            reasons = (("keyword_match",) if matches else ()) + (("severity",) if item.severity > 0 else ())
            ranked.append(Relevance(item.observation_id, score, reasons))
        return tuple(sorted(ranked, key=lambda x: (-x.score, x.observation_id)))

    def detect_anomalies(self, observations: Sequence[Observation]) -> tuple[Anomaly, ...]:
        if not observations:
            return ()
        severities = [o.severity for o in observations]
        mean = sum(severities) / len(severities)
        variance = sum((x - mean) ** 2 for x in severities) / len(severities)
        std = math.sqrt(variance)
        result = []
        for item in observations:
            deviation = abs(item.severity - mean) / (std or 1.0)
            score = min(1.0, 0.5 * item.severity + 0.5 * min(1.0, deviation / 3.0))
            if score >= self._baseline:
                result.append(Anomaly(item.observation_id, score, "severity_deviation"))
        return tuple(sorted(result, key=lambda x: (-x.score, x.observation_id)))

    def forecast(self, observations: Sequence[Observation], *, horizon: float = 3600.0, limit: int = 8) -> tuple[Forecast, ...]:
        if isinstance(horizon, bool) or not isinstance(horizon, (int, float)) or not math.isfinite(horizon) or horizon <= 0:
            raise ValueError("invalid_horizon")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 8:
            raise ValueError("invalid_forecast_limit")
        by_subject: dict[str, list[Observation]] = {}
        for item in observations:
            by_subject.setdefault(item.subject, []).append(item)
        forecasts = []
        for subject, items in by_subject.items():
            likelihood = min(1.0, sum(i.severity for i in items) / max(1, len(items)))
            evidence = tuple(i.observation_id for i in sorted(items, key=lambda x: (-x.severity, x.observation_id))[:4])
            forecasts.append(Forecast(subject, likelihood, float(horizon), evidence))
        return tuple(sorted(forecasts, key=lambda x: (-x.likelihood, x.subject))[:limit])

    def analyze(self, observations: Sequence[Observation], *, keywords: Sequence[str] = (), horizon: float = 3600.0) -> Mapping[str, tuple]:
        bounded = tuple(observations[:MAX_EVENTS])
        if len(bounded) != len(observations):
            raise ValueError("observation_batch_exceeded")
        return {
            "relevance": self.rank_relevance(bounded, keywords=keywords),
            "anomalies": self.detect_anomalies(bounded),
            "forecasts": self.forecast(bounded, horizon=horizon),
        }
