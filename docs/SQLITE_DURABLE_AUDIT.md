# SQLite durable audit chain

`SQLiteAuditLog` implements the existing `AuditLog` contract as a SQLite-backed
append-only event chain. It can be passed to components that require an
`AuditLog` instance, including the audited ExecutionFabric decorator.

## Guarantees

- WAL journal mode and `synchronous=FULL` for committed writes.
- `BEGIN IMMEDIATE` serializes writers across threads and processes.
- The previous digest is read inside the same transaction as the append.
- Events are canonical JSON; non-JSON values and NaN/Infinity are rejected.
- Integrity verification recomputes every link and checks contiguous sequence
  numbers. A restart reloads the persisted chain.
- The existing authenticated checkpoint contract is retained.

## Boundary

A local hash chain detects edits, deletion, insertion, and reordering within the
database. It cannot detect replacement of the whole database with an older,
internally valid copy. That requires an independently stored authenticated
checkpoint (for example, a remote witness or protected key provider). This
module does not claim distributed consensus, WORM storage, or HSM-backed keys.

## Use

```python
from core.sqlite_audit import SQLiteAuditLog

audit = SQLiteAuditLog("/var/lib/noryx7/audit.sqlite")
try:
    audit.record("runtime.started", runtime_id="node-a")
finally:
    audit.close()
```
