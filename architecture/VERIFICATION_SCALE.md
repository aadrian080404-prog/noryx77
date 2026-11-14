# NORYX7 — Verification Scale

## Objective

NORYX7 is not considered production-ready because a few hundred deterministic unit tests pass. Verification must combine deterministic regression, property-based, combinatorial, adversarial, fuzz, concurrency, fault-injection, security, performance and long-duration tests.

## Test pyramid

### Tier 0 — deterministic regression
Every contract, boundary, state transition, security invariant and known defect receives a permanent regression test.

### Tier 1 — property and invariant testing
Generate large families of inputs and assert invariants rather than individual expected outputs.

### Tier 2 — combinatorial testing
Cross product execution identities, policies, capabilities, dependencies, model/tool results, memory scopes, timing and failure states within bounded generated spaces.

### Tier 3 — fuzzing
Malformed contracts, encodings, serialized state, network messages, model outputs, tool results, graph structures and recovery records.

### Tier 4 — adversarial security
Authentication, identity substitution, replay, reflection, tampering, authorization confusion, privilege escalation, state poisoning, memory isolation, capability abuse, lockdown/recovery bypass and distributed trust attacks.

### Tier 5 — concurrency and fault injection
Race schedules, cancellation, timeouts, duplicate dispatch, partial failure, process interruption, storage corruption and network partition scenarios.

### Tier 6 — performance and endurance
Latency distributions, throughput, memory pressure, bounded-resource operation, long-running executions and repeated lifecycle transitions.

### Tier 7 — system-level scenarios
End-to-end user intent through planning, routing, agent collaboration, secure dispatch, verification, commit, memory and recovery.

## Million-scale requirement

The target verification campaign is **millions of generated test cases**, not millions of hand-written test functions. A deterministic seed registry must make every generated failure reproducible.

The CI strategy should separate:

- fast mandatory regression gates;
- high-volume generated verification;
- scheduled exhaustive campaigns;
- security campaigns;
- endurance campaigns.

A green fast CI run is necessary but never sufficient to claim exhaustive verification.

## Difficulty distribution

Generated cases must intentionally span trivial, normal, boundary, pathological, adversarial and compound scenarios. Distribution must prevent the campaign from spending its entire budget on easy cases.

## Acceptance rule

A candidate can only be declared ready after:

1. architecture completeness review;
2. invariant suite passes;
3. adversarial suite passes;
4. generated campaign reaches its configured case budget;
5. no unexplained failure remains;
6. all failures are reproducible and either fixed or explicitly classified as an accepted non-defect;
7. final regression and integration CI are green.

## Important distinction

No finite test campaign can mathematically prove that arbitrary software contains zero bugs. The engineering target is therefore zero known defects plus layered evidence, strong invariants, reproducibility, fault containment and continuous regression.
