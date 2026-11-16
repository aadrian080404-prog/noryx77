# NORYX7 — Parallel integration cycle evidence

Date: 2026-11-16

This record captures exact repository evidence observed during the parallel integration cycle. A green workflow validates only the code at the listed commit and the checks that actually ran. It does not imply merge, deployment, hardware validation, or production readiness.

## Canonical gap-closure branch

- PR: #85 — `integration/noryx7-architecture-gap-closure-2026-11-16`
- Head: `9b3acc06df44edec3cc8b0614ad19d9c8f768ee2`
- Base: `main`
- State: open, draft, not merged.
- Latest observed CI:
  - Workflow run `43775434678` — NORYX7 tests: success, including integration-manifest validation and test job.
  - Workflow run `43775434675` — Runner Smoke: success.
  - Workflow run `43775434673` — Source Secrecy: success.
  - Workflow run `43775434700` — Core Verification: success.
  - Workflow run `43775434695` — JARVIS Polyglot (Go, Rust, Python): success.
  - Workflow run `43775434687` — Foundation Verification: success, including Android browser verification.
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
