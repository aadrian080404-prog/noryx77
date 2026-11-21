# ADR-003 — Canonical state, journal, commit and recovery authority

**Status:** Proposed architecture decision; source-inspected, not implemented  
**Date:** 2026-11-21  
**Scope:** durable state, execution journal, attestations, idempotency and recovery

## Context and observed source

The inspected source shows multiple state-related abstractions:

- `core/runtime.py` composes `StateStore` and optional `core.state_journal.StateJournal`.
- `core/state.py` provides the in-memory state store abstraction.
- `core/state_journal.py` is wired to the core runtime state store.
- `noryx7_runtime/engine.py` optionally accepts a separate `noryx7_runtime.state.StateJournal`, reserves action steps before dispatch, and constructs attestation-linked execution records.
- `noryx7_runtime/state.py` records principal, execution, step, agent identity fingerprint, action/output digests, signature, previous attestation digest, runtime ID and provenance seal.
- `core/recovery.py` is composed into the core runtime and HYPERSYNTH runtime.

The existence of two journal classes is not itself a defect: they may serve distinct execution domains. The unresolved issue is the lack of a single documented authority/namespace map and cross-domain consistency contract.

## Decision proposal

Adopt a **State Authority Service (SAS)** as the logical owner of durable state transitions, with separate journal implementations permitted only as explicitly registered backends/namespaces.

### Canonical layers

1. **Working Context:** ephemeral request/task context; disposable and never treated as committed truth.
2. **Execution Journal:** immutable sequence of execution lifecycle events, action reservations, dispatch outcomes and attestations.
3. **Domain State Store:** versioned business/application state derived from admitted events.
4. **Evidence/Provenance Store:** source references, claim lineage, verification artifacts and retention metadata.
5. **Recovery Checkpoint:** authenticated checkpoint of journal position, schema epoch, runtime identity and recovery epoch.
6. **Audit Record:** security/audit events; separate from user-facing telemetry and financial/business ledger.

### Required transaction protocol

```text
PROPOSE
  -> VALIDATE CONTRACT + PRINCIPAL + POLICY
  -> RESERVE IDEMPOTENCY KEY
  -> AUTHORIZE ACTION
  -> DISPATCH EXTERNAL SIDE EFFECT
  -> CAPTURE RESULT + ATTESTATION
  -> VERIFY RESULT / PROVENANCE
  -> APPEND IMMUTABLE EXECUTION EVENT
  -> COMMIT DOMAIN STATE VERSION
  -> ACKNOWLEDGE FINAL OUTCOME
```

The exact order of reservation and authorization must be finalized against the action-risk model; the invariant is that no non-idempotent dispatch occurs without a durable or equivalently strong replay barrier.

## Commit semantics

Use explicit outcome classes:

- `NOT_STARTED`: no dispatch was attempted.
- `RESERVED`: idempotency reservation exists; no dispatch is known to have occurred.
- `DISPATCHED`: target accepted or may have accepted the action.
- `ATTESTED`: execution result is bound to an authenticated executor identity.
- `ADMITTED`: result passed the required result/provenance checks.
- `COMMITTED`: domain state version was durably committed.
- `REJECTED`: action/result was rejected before commit.
- `INDETERMINATE`: external effect may have happened but durable outcome cannot be established.
- `COMPENSATION_PENDING` / `COMPENSATED`: explicit compensating workflow, never implied rollback.

A failed commit after a possible external side effect must become `INDETERMINATE`, not `FAILED_WITH_NO_EFFECT`.

## Journal ownership and namespaces

- Every journal has a stable `journal_id`, owner, namespace, schema version, signing trust root and retention policy.
- A runtime ID identifies an execution engine instance; it does not alone establish journal ownership.
- An execution ID is globally unique within its declared tenant/namespace and bound to one principal.
- A step reservation binds execution, principal, step and action digest; conflicting reuse is rejected.
- Attestation chains are scoped to a declared execution/journal sequence and cannot be silently spliced across runtimes.
- Cross-journal workflows use an explicit saga/correlation protocol; they are not presented as one ACID transaction.
- Journal replication preserves sequence, signatures, provenance and tombstones; replicas cannot independently invent commits.

## Recovery contract

Recovery must distinguish:
- process restart with intact journal;
- checkpoint restore;
- partial/corrupt journal;
- key compromise or signer revocation;
- offline partition and stale trust data;
- duplicate dispatch/replay;
- target-side unknown outcome;
- schema upgrade with pending events.

Fail closed for privileged replay if integrity, identity, sequence continuity or revocation freshness cannot be established. Recovery may restore read-only context while blocking external actions.

## Alternatives considered

- One physical journal for all subsystems: rejected as a premature implementation constraint.
- Independent journals with no shared semantics: rejected because cross-runtime recovery becomes ambiguous.
- One logical state authority with pluggable, explicitly namespaced journals: proposed.

## Open questions

- Which data classes require durable journaling versus reconstructible cache?
- Are core and operational-runtime journals intended to share a namespace?
- What is the authoritative source of time/epoch during offline recovery?
- What compensation semantics exist for each external adapter class?

## Acceptance evidence before architecture freeze

- Namespace and ownership matrix for every state/journal implementation.
- Complete lifecycle transition table, including uncertain external effects.
- Replay/idempotency key derivation and retention policy.
- Attestation trust, key rotation and revocation semantics.
- Recovery matrix for restart, corruption, partition, restore and schema migration.
- Explicit separation of audit, telemetry, evidence and business ledger.
