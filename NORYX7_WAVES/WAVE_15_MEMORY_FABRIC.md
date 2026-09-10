# WAVE 15 — MEMORY FABRIC

Dependency: Wave 14 CLOSED.

## Goal
Unify L0-L5 memory, local/global memory, secure storage, persistence, suspended/distributed memory and retention semantics.

## Must verify
- memory access is principal/execution bound;
- retention and deletion policies are enforceable;
- suspended memory is not equivalent to permanent ingestion;
- encrypted/secure storage boundaries are preserved;
- recovery restores valid state without stale authorization;
- memory writes have provenance and audit records;
- sensitive data does not leak into logs or model metadata.

## Closure tests
Write/read across tiers, restart/recovery, deletion, cross-principal isolation, stale execution access, corrupted record, concurrent writes and distributed shard disagreement.
