# NORYX7 — Parallel integration cycle evidence

Date: 2026-11-16

This record captures exact repository evidence observed during the parallel integration cycle. A green workflow validates only the code at the listed commit and the checks that actually ran. It does not imply merge, deployment, hardware validation, or production readiness.

## Canonical gap-closure branch

- PR: #85 — `integration/noryx7-architecture-gap-closure-2026-11-16`
- Head at this update: `cddbe9b4303e7fbd69877bc08c254ca58c0a65ac`
- Base: `main`
- State: open, draft, not merged.
- Latest observed CI:
  - Workflow run `43775434678` — NORYX7 tests: success, including integration-manifest validation and test job.
  - Workflow run `43775434675` — Runner Smoke: success.
  - Workflow run `43775434673` — Source Secrecy: success.
  - Workflow run `43775434700` — Core Verification: success.
  - Workflow run `43775434695` — JARVIS Polyglot (Go, Rust, Python): success.
  - Workflow run `43775434687` — Foundation Verification: success, including Android browser verification.
- Rechecked exact current head `cddbe9b4303e7fbd69877bc08c254ca58c0a65ac`: Foundation, Runner Smoke, Go, Python, Rust, both test jobs and Source Secrecy all completed successfully.
- The manifest validator reports 18 modules: 1 implemented, 8 implemented_partial, 6 candidate_only, 3 specification_only.
- The validator is a structural dependency/source-path gate. It is not a production-readiness detector.

## Candidate: quorum-backed audit witness

- PR: #66 — `integration/quorum-backed-sqlite-audit-2026-11-14`
- Head: `ac2bbe77af4a5a082911df9e22f5316aad7a8d9a`
- Base: `security/sqlite-audit-external-anchor-2026-11-14`
- State: open, draft, not merged.
- Observed check-runs: 8 of 8 completed successfully.
- Source reviewed: `core/quorum_witness.py`, `core/remote_witness.py`, integration/unit tests and protocol documentation.
- Useful implementation: nonce-bound Ed25519 receipts, odd-sized quorum, unique public-key fingerprints, compare-and-swap anchor operations and fail-closed read when no unique majority exists.
- Explicit limits: failure-domain labels are operator assertions, not proof of independent hosting/administration; the coordinator lock is process-local; the candidate does not provision independent witness services, TLS peer identity, production credentials, rollback-resistant storage or operational monitoring.
- Integration dependency: PR #66 is based on a separate SQLite external-anchor branch. Rebase/compose its complete dependency chain before considering it for the canonical line.

## Candidate: unified Python/ELF system inspector

- PR: #72 — `analysis/integrated-python-elf-system-inspection-2026-11-14`
- Head: `9af2ef8685cce1f633167a8795025d5b0120e7b5`
- Base: `analysis/bounded-elf-system-inspector-2026-11-14`
- State: open, draft, not merged.
- Observed check-runs: 8 of 8 completed successfully.
- Source reviewed: `core/system_inspector.py`, ELF integration tests and descriptor-traversal documentation.
- Useful implementation: bounded deterministic Python AST and ELF inspection; descriptor-relative traversal; no symlink following; no execution of inspected code; entry, file and byte budgets.
- Explicit limits: static findings are triage leads, not proof of exploitability; ELF format coverage is limited; dynamic inspection requires a separately provisioned OS-isolated sandbox; descriptor flags are platform-dependent.
- Integration dependency: PR #72 is based on a separate bounded-ELF-inspector branch. Reconcile that base dependency before canonical integration.

## Parallel-cycle decisions

1. Keep #66 and #72 classified as `candidate_only` in the integration manifest until their full base dependency chains are present on the canonical integration line.
2. Do not wire quorum or system-inspector code into the production runtime merely because candidate CI is green.
3. Next integration gates are independent witness provisioning and failure-domain verification; target-side execution fencing for Matrix; durable offline outbox with crash/restart tests; stable key custody and verified principal binding; and one gateway-to-agent-to-model-to-audit end-to-end test path.
4. Continue using isolated draft PRs. No changes to `main`, the frozen architecture branch, or production deployment are authorized by this cycle.

## Evidence semantics

- `CI-verified`: the exact commit passed the recorded CI jobs.
- `candidate-only`: code remains on an unmerged branch and is not importable from the audited main branch.
- `integrated`: dependency-complete source is present on the canonical integration line and its integration tests pass.
- `hardware-verified` / `production-verified`: require separate device, deployment, security, recovery and operational evidence; neither status is claimed here.


## Follow-on implementation — durable local outbox

- PR: #86 — `integration/durable-offline-outbox-sqlite-2026-11-16`
- Latest head: `ceccfda0777faab2358111779ec95b236644199c`
- Base: PR #85 integration head `22b772fa01ac8fe70c4ea82c916d7fd41abdac2e`.
- Exact commit CI: NORYX7 tests, Core Verification, Foundation Verification, Runner Smoke and Source Secrecy all completed successfully.
- Test result: `789 passed in 7.53s`.
- The initial test revision failed because its deliberately transparent cipher test double did not meet the ciphertext-opacity assertion; the test double was corrected to use a deterministic opaque transform. This is test-only and is not a production cipher.
- Scope: local SQLite ciphertext outbox, metadata/digest, transaction, idempotent enqueue, capacity and restart semantics.
- Not included: durable OfflineRuntime state/snapshot, stable production cipher/KMS, rollback-resistant anchor, exactly-once remote side effects, distributed replication.

## Follow-on implementation — durable key lifecycle metadata

- PR: #87 — `security/sqlite-key-lifecycle-metadata-2026-11-16`
- Head: `24682e9dd3930ca4e5455eeb46e0d68a2814fe3c`
- Base: PR #85 integration head `22b772fa01ac8fe70c4ea82c916d7fd41abdac2e`.
- NORYX7 tests completed successfully: `789 passed in 7.53s`.
- Source Secrecy and Runner Smoke completed successfully.
- Core Verification and Foundation Verification were still running at the time this evidence record was updated.
- Scope: durable SQLite metadata for key IDs, versions, active/retiring/revoked state; transactional transitions, startup validation, cross-connection visibility.
- Not included: secret/private key material, KMS/HSM, key wrapping, hardware-backed custody or anti-rollback against database snapshot restoration.


## Follow-on implementation — Matrix target-side generation fence

- PR: #88 — `matrix/target-side-generation-fenced-executor-2026-11-16`
- Exact head: `f623fcefbc54f0ccc995b66d73fcea2670c97acb`
- Base: PR #83 durable Matrix stop-intent branch, head `26904351fa45d983b19c69ca124d83fbf8f78e9e`.
- Exact-head checks: Foundation, tests (both jobs), Runner Smoke and Source Secrecy all completed successfully.
- Follow-up corrections after the initial test-collection failure: complete target adapter implementation, durable pre-launch `starting` intent, grant/task-state recheck under SQLite write lock, legacy schema migration and recovery tests.
- Scope: target-local generation fencing and durable stop/start intent.
- Limits: no OS sandbox, no proof of process termination, no cross-device consensus, and no independent process supervisor. The wrapped executor must provide idempotent, linearizable task start/stop semantics.

## Follow-on implementation — bounded authorization replay cache

- PR: #89 — `security/bounded-authorization-replay-cache-2026-11-16`
- Exact head: `d3a2f8adfa6e0ac7004fa106d9e7ec44bd0294c4`
- Exact-head status at update: both test jobs, Runner Smoke and Source Secrecy succeeded; Foundation was still running.
- Scope: bounded expiry-aware consumed-grant nonce cache; cache saturation denies rather than evicting valid replay records; expired entries are reclaimed.
- Limit: process-local only; multi-instance replay protection requires a shared transactional nonce store or a single authority.

## Follow-on implementation — verified offline principal binding

- PR: #90 — `security/offline-verified-principal-binding-2026-11-16`
- Exact head: `64f26abed866cbb00bb11b2e93374871a0670532`
- Exact-head status at update: Runner Smoke succeeded; both test jobs, Foundation and Source Secrecy were still running.
- Scope: execution IDs are no longer silently treated as principals; offline execution requires a principal ID, key fingerprint, trusted authenticator and snapshot/principal match before local execution.
- Limit: production wiring must connect the authenticator to a trusted user/device identity provider and protected key lifecycle. Test callbacks do not establish production identity.

## Follow-on implementation — audit concurrency

- PR: #91 — `security/audit-concurrency-checkpoint-2026-11-16`
- Exact head: `34430abd0484ec9e37c7b45bbdfb6e58db561f4d`
- Exact-head status at update: Foundation, tests, Runner Smoke and Source Secrecy were still running.
- Scope: serialized audit-chain append/snapshot/digest/integrity access; key-provider I/O remains outside the lock; checkpoint verification rechecks the chain head after key-provider I/O.
- Limit: the log remains in-memory and process-local; concurrency safety does not make it durable or independently anchored.
