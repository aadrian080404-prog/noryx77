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


## 6. AuditLog append operations are not synchronized

**Status: CONFIRMED / concurrency-integrity defect**

In `core/audit.py`, `record()` reads the current chain tail, calculates the next digest, and appends to `_events` and `_digests` without a lock. `snapshot()`, `verify_integrity()`, and `digest()` also read mutable chain state without synchronization. Concurrent writers can observe the same previous digest and append sibling entries into a linear-chain structure, or readers can observe an intermediate state between the two appends.

**Required correction:** serialize record/verify/snapshot/checkpoint operations with a re-entrant lock, or use an append transaction in the durable backend. Define whether checkpoints hold the lock for their full snapshot operation. Do not perform remote key-provider I/O while holding the chain lock unless the provider contract explicitly guarantees bounded local behavior.

**Acceptance tests:** concurrent multi-thread appends preserve a single verifiable chain; snapshots are internally consistent during writes; checkpoint digest corresponds to a consistent chain prefix.

## 7. MemoryHierarchy is a weaker parallel memory implementation

**Status: CONFIRMED / inconsistent contract**

`core/memory_hierarchy.py` currently exposes a small in-memory dictionary implementation alongside the more strongly validated `MemoryStore` and encrypted `EncryptedMemoryStore`.

Observed gaps:
- no synchronization around capacity check, put, get or promote;
- `max_records=True` passes the numeric range check because booleans are integers in Python;
- `put()` does not validate the record type, key/value types, or that level is a `MemoryLevel`;
- `promote()` relies on raw dictionary indexing and accepts an unchecked level;
- no persistence, encryption, execution/principal isolation, or promotion policy is implemented in this class.

**Required correction:** either make this a clearly named low-level volatile index over the canonical memory stores, or retire it from operational routing. If retained as an API, add strict validation, synchronization and an explicit ownership/isolation key. Do not present L0-L5 labels as proof that storage tiers, retention, or distributed memory are operational.

**Acceptance tests:** reject bool capacity and malformed records; concurrent capacity-bound writes never exceed capacity; invalid promotion fails with a stable error; memory ownership/isolation is tested.

## 8. EncryptedMemoryStore does not share MemoryStore's validation boundary

**Status: CONFIRMED / data-contract inconsistency**

`core/secure_memory.py` serializes any `MemoryItem` without applying the full validation in `MemoryStore.put()`. Its deserializer checks that `importance` is numeric but does not enforce finiteness and the 0..1 range, and it checks `kind` is text but not that it belongs to `MemoryStore.VALID_KINDS`. This means callers can persist records that the in-memory store would reject, and those records can be returned by the encrypted store.

**Required correction:** centralize MemoryItem validation and invoke it before serialization and after deserialization. Ensure schema migration is explicit and malformed authenticated records fail closed.

**Acceptance tests:** NaN/infinite/out-of-range importance and unknown kinds are rejected both before persistence and after loading; valid records round-trip unchanged.

## 9. Gateway session-secret strength and lifecycle need an explicit policy

**Status: CONFIRMED / authentication hardening gap**

`gateway/auth.py:SessionAuthority.__init__()` checks only that the bootstrap token and signing secret are non-empty. It accepts arbitrarily short signing secrets and bootstrap tokens. The session token is stateless: the generated nonce is not tracked, and there is no revocation/rotation mechanism in this class. The HTTP gateway also has no visible per-client rate-limit boundary around bootstrap session issuance.

**Required correction:** enforce a minimum signing-secret entropy/length (prefer a generated 32-byte or stronger secret), define bootstrap-token rotation and secure provisioning, and add a revocation/version mechanism if sessions must be invalidated before expiry. Apply rate limiting and abuse controls at the gateway/reverse-proxy boundary; do not mistake a random nonce in a stateless token for replay prevention or revocation.

**Acceptance tests:** weak secrets are rejected; secret rotation invalidates old sessions according to policy; revoked sessions fail immediately; bootstrap attempts are rate-limited at the actual HTTP boundary.

## Updated integration priority

| Priority | Area | Blocking condition | Required gate |
|---|---|---|---|
| P0 | Gateway bootstrap | Default entry point cannot build its runtime | Factory and startup tests |
| P0 | Matrix revocation | Retry can stop healthy workloads | Pending-stop isolation tests |
| P0 | Audit | Concurrent appends can break linear-chain consistency | Concurrent append/checkpoint tests |
| P1 | Model result proof | Optional key means no cryptographic authentication | Explicit integrity/authentication modes |
| P1 | Provider adapter | Unbounded response reads | Bounded streaming tests |
| P1 | Session authority | Weak secrets and no revocation/rate-limit contract | Secret, rotation, revocation and abuse tests |
| P1 | Memory | Multiple stores expose inconsistent validation/isolation semantics | Canonical validation and ownership tests |
| P2 | Provider economics | Zero cost is a placeholder, not measured cost | Usage-aware accounting contract |

## 10. Cross-PR coverage pass — existing candidate branches (2026-11-15)

This pass compared the findings above against existing feature branches and inspected the exact candidate source/test files. A branch containing a correction is not equivalent to a merged or CI-verified correction.

| Finding | Candidate branch / source evidence | Regression evidence inspected | Current disposition |
|---|---|---|---|
| AuditLog concurrency | `security/audit-log-concurrency-2026-11-14` adds an `RLock`; record, snapshot, digest, integrity verification and checkpoint paths use a consistent lock strategy. Key-provider I/O is outside the chain lock, followed by a second consistency check. | `tests/test_audit_concurrency.py`: 500 concurrent appends, concurrent snapshots/verifications, checkpoint consistency. | **Candidate correction exists; not merged and not executed in this pass.** Needs CI on the candidate head and review of its broader 89-file branch diff before integration. |
| MemoryHierarchy validation/thread safety | `memory/hierarchy-thread-safety-validation-2026-11-14` adds an `RLock`, strict non-bool integer capacity validation, bounded key/value validation, record/level type checks, safe lookup, delete and snapshot. | `tests/test_memory_hierarchy_hardening.py`: invalid capacities/records, bounds, promotion/deletion, concurrent capacity writes. | **Candidate correction exists; not merged and not executed in this pass.** It explicitly documents this as process-local, not distributed memory. Ownership isolation is still not implemented by this class and must remain an explicit architectural boundary. |
| EncryptedMemoryStore validation parity | Compared `core/secure_memory.py` on main and `hardening/encrypted-memory-store-concurrency-2026-11-13`; the file is unchanged and the candidate diff does not include it. | No regression test for the identified NaN/Inf/range/allowed-kind mismatch was found in the inspected candidate files. | **Unresolved.** The encrypted SQLite adapter work in PR #20 is a separate concern and does not, by itself, close this validation-parity defect. |
| Matrix revocation retry | Re-inspected `core/matrix_supervisor.py` on `architecture/noryx7-matrix-core-2026-11-14`; `retry_pending_stops()` still iterates `_active`, and successful dispatch still populates `_active`. | Existing `core/test_matrix_supervisor.py` is part of the branch, but the required active-workload/no-revocation regression was not demonstrated by the inspected source. | **Unresolved P0.** A separate pending-stop set and targeted tests remain required. |
| Gateway bootstrap | Main still defaults through `NoryxGateway -> RuntimeAdapter -> OperationalNORYXRuntime()`, while the provider-injected factory remains in `noryx7_operational.py`. No inspected gateway branch closes this call-path gap. | Required startup/factory tests remain acceptance criteria. | **Unresolved P0.** |
| Session authority | Main `gateway/auth.py` still accepts any non-empty bootstrap/signing secrets and does not implement session revocation or a gateway rate-limit boundary. | Required weak-secret, rotation, revocation and HTTP rate-limit tests remain acceptance criteria. | **Unresolved P1.** |
| Model result authentication | Main operational factory still constructs `ModelFabric` without a binding key. | Required explicit unauthenticated-vs-authenticated mode tests remain acceptance criteria. | **Unresolved P1.** |
| OpenRouter response bounds | Main adapter still requires bounded incremental reads on success and error paths. | Required oversized-body and malformed-response tests remain acceptance criteria. | **Unresolved P1.** |
| Provider economics | Adapter contract still lacks authoritative usage/cost reconciliation. | Required usage metadata/accounting contract remains acceptance criteria. | **Unresolved P2.** |

### Integration rules from this pass

1. Do not cherry-pick either broad candidate branch wholesale: each is ahead of main by many commits and changes dozens of unrelated files. Extract only the reviewed feature delta after ancestry, tests and file overlap are reconciled.
2. The audit and memory-hierarchy candidate branches are promising source-level corrections, not verified releases. Run their focused tests and all required CI before calling them complete.
3. Do not confuse PR #20's encrypted SQLite transaction/concurrency work with validation parity in `core/secure_memory.py`, nor with distributed multi-device memory.
4. Keep the Matrix revocation fix isolated to its own branch because it is a safety-critical behavioral correction in a new subsystem.
5. No application code, PR state, deployment, or frozen branch was changed by this coverage pass. The six PR #75 workflows for commit `5c489f4016db99b2706d00be984282d361971389` subsequently completed successfully; this validates the documentation commit's configured CI, not the candidate branches or production behavior.

## 11. Isolated remediation PRs opened (2026-11-15)

The following source-level corrections have now been extracted into small, isolated draft PRs. They are separate from this architecture/documentation PR and remain unmerged.

| PR | Workstream | Exact change | Verification state at register update |
|---|---|---|---|
| [#73](https://github.com/aadrian080404-prog/noryx77/pull/73) | Matrix stop retry | Adds `_pending_stops`; only failed revocation stop requests are retried. Adds tests proving a healthy active task is not stopped by a retry call and only failed task IDs are retried. | Tests, Core, JARVIS, Runner Smoke and Source Secrecy passed on head `9c286ca`; Foundation remains pending. Restart durability of pending stops remains unresolved and is not claimed. |
| [#76](https://github.com/aadrian080404-prog/noryx77/pull/76) | Gateway bootstrap | Default `RuntimeAdapter` now lazily calls canonical `noryx7_operational.build_runtime()`; injected runtime/factory remain supported. Adds factory/injection tests. | Tests, Core, JARVIS, Runner Smoke and Source Secrecy passed on head `ec9d962`; Foundation remains in progress. |
| [#77](https://github.com/aadrian080404-prog/noryx77/pull/77) | Audit concurrency | Extracts only synchronized `core/audit.py` and focused concurrent append/snapshot/checkpoint tests from the broad candidate branch. | All six configured workflows passed on head `086e308`. |
| [#78](https://github.com/aadrian080404-prog/noryx77/pull/78) | Memory hierarchy | Extracts only validated, synchronized process-local `MemoryHierarchy` and focused hardening tests. | Tests, Core, JARVIS, Runner Smoke and Source Secrecy passed on head `ba8757d`; Foundation remains in progress. |
| [#79](https://github.com/aadrian080404-prog/noryx77/pull/79) | OpenRouter response bounds | Adds bounded chunk reads, content-length precheck, content-type validation and bounded HTTP error bodies with focused tests. | Tests, Core, JARVIS, Runner Smoke and Source Secrecy passed on head `3c90fd8`; Foundation remains in progress. |
| [#80](https://github.com/aadrian080404-prog/noryx77/pull/80) | Encrypted memory validation | Shares canonical `MemoryStore` validation across plaintext and encrypted writes/loads, with invalid numeric/kind regressions. | Workflow runs not yet returned for head `7e4859e`; pending verification. |

### Remaining integration gates

- Matrix: persist pending stop intents durably across supervisor restart, and prove target-side generation fencing. The current PR fixes the live retry selection bug but does not yet close crash recovery.
- Gateway: test startup with a real configured provider in a controlled environment and verify shutdown cleanup if construction partially succeeds.
- Audit: all six configured workflows passed for PR #77 head `086e308`; still review checkpoint key rotation and external provider failure behavior before integration.
- Memory: centralize validation across `MemoryStore` and `EncryptedMemoryStore`; add the missing NaN/Inf/range/kind regression tests and explicit principal isolation before presenting memory as a complete multi-device service.
- All four PRs remain draft, unmerged, and not deployed. Green individual workflows do not establish full system integration.
