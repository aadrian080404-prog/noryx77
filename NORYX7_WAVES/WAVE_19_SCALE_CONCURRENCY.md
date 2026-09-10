# WAVE 19 — SCALE, CONCURRENCY & PERFORMANCE

Dependency: Wave 18 CLOSED.

## Goal
Move from correctness under ordinary tests to correctness under high concurrency, million-case campaigns, sustained load and resource pressure.

## Must verify
- million-case verification remains deterministic and category-balanced;
- concurrent execution preserves identity, replay and state invariants;
- queues have bounded backpressure;
- resource/model budgets are enforced;
- cancellation is propagated;
- latency and memory growth remain bounded;
- failures do not corrupt shared state;
- rate limits cannot bypass authorization.

## Closure tests
1M+ deterministic campaign, concurrent sessions, burst load, long duration, cancellation storms, provider latency, memory pressure, queue saturation and recovery under load.
