# NORYX7 Integrated Security Workstreams

Status date: 2026-11-13
Working branch: `repair/ci-dependency-preflight-2026-11-13`
Integration PR: #8 (open; not merged)
Separate SURF PR: #7 (open; not merged)

This document is the cross-workstream status ledger. A design, interface, synthetic test, or passing CI run is not evidence of production readiness.

## 1. Workstreams now progressing in parallel

| Workstream | Current code evidence | Boundary / not yet delivered |
|---|---|---|
| Runtime authorization | PR #8: risk-class propagation, capability registry enforcement, persistent replay guard for privileged RuntimeEngine actions, authorization-bound action statements | Does not eliminate every in-memory authorization path or provide globally rollback-resistant replay consensus |
| Adversarial simulation | `core/adversarial_game.py`: deterministic bounded max-min game over an abstract security state; unit tests cover replay, tampering, exfiltration, disruption and defensive moves | Not SEAT, not a learned attacker, not AlphaZero, not a live red-team, not production telemetry, and not a calibrated probability model |
| Institutional access | `core/institutional_access.py`: signed-mandate and approval-verification interfaces, purpose/jurisdiction/scope/expiry/output limits, exact request binding, M-of-N independent-domain and role checks | Policy gate only. It does not query or release data, implement zk-SNARKs, guarantee deletion/non-retention, or establish legal admissibility. Production requires a real cryptographic verifier and independently governed approver registry |
| SURF system understanding | PR #7: bounded evidence-grounded architecture, contracts and assessment/experiment gate | Separate branch; not yet integrated with PR #8, and live observation adapters plus trusted sandbox receipts remain outstanding |
| Encrypted data plane | `core/secure_data_plane.py`: per-record AES-GCM envelope primitive with injected key provider | Not wired through all persistence, backups, logs, browser storage, streaming, or distributed replication |
| Cognitive state journal | `core/state_journal.py`: SQLite durability, canonical records, sequence checks, unkeyed SHA-256 tamper detection | Unkeyed digest is not authenticity; no external key custody or independent rollback anchor |
| Runtime execution journal | `noryx7_runtime/state.py`: signed attestation checks and in-process chain/reservation semantics | Separate from cognitive SQLite journal; not yet a unified durable transaction journal |
| Memory and global fabric | Existing memory hierarchy and metadata/index components | Not a complete encrypted, distributed, tenant-isolated, recoverable memory service |
| Independent assurance | Existing verification callbacks and consensus checks | Trusted verifier registry, independent signed receipts, and enforceable verifier separation remain incomplete |

## 2. Security invariants shared across the workstreams

1. Deny by default; failure of identity, policy, clock, signature verification, key access, or replay protection must not grant authority.
2. Bind approvals to the exact canonical request, including the full signed mandate digest, purpose, jurisdiction, data scopes, mode, output limit, and request identity.
3. Distinct approver IDs are insufficient by themselves: quorum members must also belong to distinct trusted independence domains and satisfy distinct required roles.
4. Adversarial simulation is abstract and bounded. It must not gain network, shell, filesystem, tool, or production-control access.
5. A model-generated hypothesis is not evidence. Preserve supporting and contradicting observations, provenance, freshness, and uncertainty.
6. A high-risk action requires independent authorization and post-action verification. A score or model consensus never authorizes it.
7. Unknown external transaction outcomes must be reconciled before retry; never assume timeout means failure.
8. No plaintext fallback when encryption or key management is unavailable.
9. Destruction of a temporary VM or key does not prove that disclosed information was not copied or retained elsewhere.
10. Do not claim global scale, unhackability, legal deniability, or production readiness from unit tests or synthetic campaigns.

## 3. Required integration sequence

### Track A — state, identity, and authorization
- Introduce keyed journal authenticity with externally managed keys and key rotation.
- Add an independently stored monotonic checkpoint/epoch to detect rollback; a local SQLite database alone cannot establish rollback resistance.
- Unify state commit and runtime execution lifecycle without weakening the existing pre-dispatch reservation and fail-closed behavior.
- Make one-shot authorization durable on every privileged path, not only selected RuntimeEngine paths.
- Define cancellation and recovery semantics for blocked or uncertain external side effects.

### Track B — adversarial intelligence and assurance
- Keep the current game kernel as a deterministic baseline.
- Add explicit evidence objects and hypothesis records before adding model-generated attack strategies.
- Implement SEAT, separate attacker/defender policies, frozen reference policy, and independent jury only behind isolated scenario adapters.
- The jury must be able to return inconclusive; agreement between models is not proof.
- Learn from verified defensive outcomes and failed mitigations as well as attacks. Do not train on unverified predictions as ground truth.

### Track C — institutional access and privacy
- Connect the current policy gate to a production-grade mandate issuer, identity registry, HSM-backed signature verification, revocation source, and append-only independent audit.
- Define each mode's permitted output schema and maximum disclosure; predicate/aggregate first, supervised reconstruction only by exception.
- Require purpose limitation, jurisdiction checks, necessity/proportionality review, challenge/appeal and retention rules.
- Treat any plaintext delivered to an institution as disclosed; downstream retention cannot be cryptographically prevented by NORYX7.

### Track D — SURF and data plane
- Review PR #7 against the current PR #8 contracts before integrating; resolve naming, trust, evidence and runtime-boundary conflicts rather than blindly merging branches.
- Require owned/authorized targets, isolated sandboxes, immutable experiment inputs, reproducible observations and signed evidence receipts.
- Wire encryption and key management into each storage adapter independently; inventory every path before claiming coverage.

## 4. Verification gates

Each implementation change must pass:
- focused unit and contract tests;
- malformed-input, type-confusion, boundary and oversized-input tests;
- concurrency, replay, restart, expiry and clock-failure tests where applicable;
- tampering, rollback and storage-failure tests for persistence;
- dependency and full Python regression suites;
- generated-scenario checks with explicit bounds;
- Android/browser and polyglot checks when affected;
- independent security review before production use.

A CI result applies only to the exact commit SHA it tested. New commits invalidate earlier pass claims until their own required checks complete.

## 5. Explicit exclusions

The current institutional gate does not include a feature called NArKoS or claim legally non-preservable evidence. Cryptography cannot guarantee that a recipient will forget, delete, or refrain from copying plaintext.

The current adversarial game kernel is not a self-evolving AI. SEAT, MetaMorphSES, multi-model jury, AlphaZero-like self-play, and Anchored Bipolicy remain separate future components requiring training isolation, reproducible evaluation, model provenance, rollback and safety gates.

The current work does not authorize live attacks, autonomous exploitation, unapproved financial transactions, or institutional disclosure. Those require separate domain adapters and approvals.

