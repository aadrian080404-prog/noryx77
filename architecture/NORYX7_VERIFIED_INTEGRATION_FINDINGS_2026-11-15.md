# NORYX7 — Verified Integration Findings (2026-11-15)

**Scope:** read-only source inspection of `main` plus review of draft PR #73.  
**Purpose:** turn concrete cross-layer defects into tracked integration gates.  
**No application code was changed by this assessment.**

## Status vocabulary

- **CONFIRMED** — directly follows from the inspected call graph or implementation.
- **REQUIRES TEST** — a regression test is needed before a correction can be considered integrated.
- **NOT CLAIMED** — no production-grade guarantee is inferred from a reference implementation.

## 1. Gateway bootstrap cannot construct its default runtime

**Status: CONFIRMED / startup blocker**

Observed call chain:

1. `gateway/__main__.py:main()` constructs `NoryxGateway()`.
2. `gateway/server.py:NoryxGateway.__init__()` defaults to `RuntimeAdapter()`.
3. `gateway/runtime_adapter.py:RuntimeAdapter.__init__()` defaults to `OperationalNORYXRuntime()`.
4. `core/operational_runtime.py:OperationalNORYXRuntime.__init__()` rejects `model_fabric=None` with `ValueError("model_fabric_required_for_operational_agents")`.

The repository already has a provider bootstrap in `noryx7_operational.py:build_runtime()`, which validates `OPENROUTER_API_KEY`, constructs `OpenRouterAdapter` and `ModelFabric`, and injects the fabric. The gateway default path does not call this factory.

**Required correction:** make gateway startup use one canonical, injectable runtime factory. Keep dependency injection for tests; fail with an explicit configuration error if provider configuration is absent. Do not silently instantiate a partial runtime.

**Acceptance tests:**
- gateway factory builds a runtime when valid provider configuration is supplied;
- missing provider configuration fails with a stable, explicit startup error;
- injected fake/runtime instance avoids provider/network access in gateway unit tests;
- `python -m gateway` reaches server startup only after successful runtime construction.

## 2. Matrix retry method can stop healthy workloads

**Status: CONFIRMED / safety defect in draft PR #73**

In `core/matrix_supervisor.py`, `dispatch()` adds every successfully started workload to `_active`. `retry_pending_stops()` iterates over all of `_active` and calls `executor.stop()` for each entry. Therefore calling the retry method during normal operation can stop workloads that were never revoked and have no failed stop request.

The issue was recorded in a review comment on PR #73 (review ID `5913254331`). The review requests a distinct pending-stop collection, populated only after a stop failure, plus regression tests. A change-request review could not be submitted because the connected account owns the PR; a normal review comment was successfully recorded.

**Required correction:** keep active workloads and pending stop retries as separate state. Retrying must only call stop for task/generation pairs whose previous stop failed.

**Acceptance tests:**
- active workload + retry before revocation => no stop call;
- one failed stop among several active tasks => only that task is retried;
- successful retry clears pending state; failed retry remains visible;
- restart/recovery preserves enough durable information to resume required drains without stopping unrelated work.

## 3. Model result integrity is not necessarily cryptographic authentication

**Status: CONFIRMED / security contract gap**

In `noryx7_runtime/model_fabric.py`, `binding_key` is optional. When it is absent, `_result_mac()` returns the deterministic envelope digest, and `verify_result()` compares that digest. This detects accidental or unauthenticated modification only to the extent that the verifier recomputes the digest; it is not a keyed MAC and does not authenticate the result's origin.

The operational factory in `noryx7_operational.py` constructs `ModelFabric([adapter], runtime_id=...)` without a binding key.

**Required correction:** distinguish integrity digest from authenticated result proof in names, types, and policy. If an authenticated result is a security requirement, require a runtime-bound secret key from an approved key provider; fail closed when unavailable. Do not describe an unkeyed digest as an HMAC/MAC or authenticated provenance.

**Acceptance tests:**
- no-key mode is explicitly classified as unauthenticated integrity mode;
- authenticated mode rejects missing, wrong, or rotated keys;
- runtime and execution binding are verified at the trust boundary;
- logs and API responses do not overstate provider identity or independent verification.

## 4. OpenRouter response bodies are not bounded before decoding

**Status: CONFIRMED / resource-exhaustion exposure**

In `noryx7_runtime/model_adapters/openrouter.py`, both the successful response path and the HTTP error path call `response.read()` / `exc.read()` before any size limit is applied. Truncating an error string after reading does not bound memory consumption. The successful JSON body is also decoded in full.

**Required correction:** impose a configurable, conservative maximum response byte count; read incrementally and abort once the limit is exceeded; apply the bound to error bodies as well as success bodies. Validate content type and response structure after the byte bound. Keep timeout and cancellation behavior explicit.

**Acceptance tests:**
- oversized success body rejected before unbounded allocation;
- oversized error body rejected/bounded;
- malformed UTF-8/JSON and non-JSON responses fail closed;
- ordinary valid response still parses.

## 5. Provider economics are currently placeholders

**Status: CONFIRMED / accounting limitation**

The OpenRouter adapter sets `cost_per_call = 0.0` and a fixed expected latency. The adapter contract returns a string, so the current interface does not carry authoritative usage, token counts, provider billing, or actual cost.

**Required correction:** mark these values as estimates/unknown rather than actual cost. Extend provider result metadata to carry reported usage when available, preserve the provider response ID and model identity, and reconcile estimates against billing data where available. A zero configured estimate must not be interpreted as proof that a request is free.

## Integration priority

| Priority | Area | Blocking condition | Required gate |
|---|---|---|---|
| P0 | Gateway bootstrap | Default entry point cannot build its runtime | Factory and startup tests |
| P0 | Matrix revocation | Retry can stop healthy workloads | Pending-stop isolation tests |
| P1 | Model result proof | Optional key means no cryptographic authentication | Explicit integrity/authentication modes |
| P1 | Provider adapter | Unbounded response reads | Bounded streaming tests |
| P2 | Provider economics | Zero cost is a placeholder, not measured cost | Usage-aware accounting contract |

## Boundaries and non-claims

- PR #73 remains draft; its green CI does not invalidate the newly identified behavioral defect.
- PR #75 is an architecture/documentation branch. This register does not itself fix the source code.
- No merge, production deployment, independent security audit, distributed consensus, hardware attestation, or OS-level process termination is claimed.
- Fixes must be made on isolated branches, tested against the relevant regression suites, and integrated only after dependency and overlap review.
