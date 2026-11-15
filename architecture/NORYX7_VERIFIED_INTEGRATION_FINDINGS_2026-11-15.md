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
| [#73](https://github.com/aadrian080404-prog/noryx77/pull/73) | Matrix stop retry | Adds `_pending_stops`; only failed revocation stop requests are retried. Adds tests proving a healthy active task is not stopped by a retry call and only failed task IDs are retried. | Tests, Core, JARVIS, Runner Smoke and Source Secrecy passed on head `9c286ca`; Foundation remains in progress. Restart durability of pending stops remains unresolved and is not claimed. |
| [#76](https://github.com/aadrian080404-prog/noryx77/pull/76) | Gateway bootstrap | Default `RuntimeAdapter` now lazily calls canonical `noryx7_operational.build_runtime()`; injected runtime/factory remain supported. Adds factory/injection tests. | All six configured workflows passed on head `ec9d962`. |
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


## 11. Follow-up verification and remediation snapshot — 2026-11-15

This section records results observed after the prior candidate-coverage pass. CI status is tied to the exact commit SHA; a green PR is still unmerged and is not a production deployment.

### CI results observed

| PR | Commit | Checks | Disposition |
|---|---|---|---|
| #73 Matrix Core | `9c286ca01f5963c2410b8dc0473ea0733f779f20` | 6/6 success | Candidate tests pass; durable pending-stop recovery remains open |
| #76 Gateway runtime bootstrap | `ec9d96274245a755fb501d772054d81b3790bc6e` | 6/6 success | Candidate tests pass; no production provider/deploy verification |
| #77 Audit concurrency | `086e308980a11285c4b2f6c4f1139bc8e8fc978c` | 6/6 success | Candidate tests pass; key-provider lifecycle review remains open |
| #78 MemoryHierarchy | `ba8757d4adc49d93f0e7ad08664dcb1ff3ec1432` | 5 success, Foundation failure | Python compile and complete pytest suite succeeded; Browser verification failed during Gradle dependency resolution because Maven Central returned HTTP 429 for multiple artifacts. This is an external dependency-fetch/rate-limit failure, not evidence of a MemoryHierarchy test failure. The PR remains unverified overall. |
| #79 OpenRouter bounded reads | `3c90fd851beb9cdc7aa78815d5fd7427e2193c5d` | 6/6 success | Candidate tests pass; no live provider request |
| #80 Encrypted memory validation | `7e4859e664bfc80cca57da47a19ea4b611f71284` | 6/6 success | Candidate tests pass; no principal isolation or distributed persistence claim |
| #75 Architecture register | `55619fd4306ac2c73d1c78efafaa5b40ffbfdb01` | 5 success, Foundation in progress at last poll | Documentation branch only; final Foundation result not yet observed |

The #78 Foundation job log identifies the failing step as **Verify NORYX Browser**. Gradle could not resolve several Android build dependencies because requests to `repo.maven.apache.org` returned HTTP 429. This must be handled as a CI supply-chain/repository-availability issue, not hidden by relabeling the check green. Repeated immediate retries are not a durable mitigation; inspect caching and repository routing before changing build configuration.

### Matrix revocation: remaining crash-recovery gap

PR #73 now separates `_pending_stops` from `_active`, so retrying failed stop requests no longer targets every healthy workload. However, `_pending_stops` is still an in-memory dictionary. The supervisor reconstructs `_active` from durable reservations on startup, while revocation reconciles/releases cancelled reservations before issuing executor stop calls. A process crash after durable revocation but before successful target termination can therefore lose the local retry list. This is **not** durable drain recovery.

Required next increment:
- persist stop intents (task ID, target node, grant generation, reason, creation time, status) before clearing/releasing the durable reservation;
- make stop completion idempotent and persist acknowledgement only after the target confirms the exact task/generation is stopped;
- rehydrate pending intents on supervisor startup;
- reject stale generations at the target executor atomically;
- test crash points before stop, after stop but before acknowledgement, and during repeated retry.

### Model Fabric: explicit authentication state added in PR #81

PR #81 (`fix/modelfabric-explicit-authenticated-results-2026-11-15`) adds an explicit `FabricResult.authenticated` marker, `ModelFabric.authenticated_results`, `verify_authenticated_result()`, and opt-in `require_authenticated_results`. Unkeyed SHA-256 envelope checking remains available for compatibility but is explicitly classified as unauthenticated. Authenticated mode requires a runtime-bound key of at least 32 bytes. Key provisioning, rotation, persistence, and KMS/HSM integration remain open. PR #81 is draft and its CI had not yet appeared at the time of this update.

### Current disposition

- #73, #76, #77, #79 and #80 have green candidate CI, but none is merged.
- #78 has an infrastructure-related Foundation failure and must not be described as fully green.
- #81 is a new draft remediation; its CI and integration with the operational factory are pending.
- Gateway session secret strength, revocation/versioning, and HTTP-boundary rate limiting remain unresolved.
- No cross-device consensus, hardware attestation, OS-level process termination, production KMS, production deployment, or independent security certification is claimed.
