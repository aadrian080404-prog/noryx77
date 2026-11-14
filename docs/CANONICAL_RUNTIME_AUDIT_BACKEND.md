# Canonical runtime audit backend selection

The canonical `NORYXRuntime` and `OperationalNORYXRuntime` now accept an
optional `audit_log` implementing the existing `AuditLog` contract. The
selected instance is shared with `HypersynthRuntime`, so HYPERSYNTH events and
runtime-level events use the same backend.

To select the durable SQLite implementation:

```python
from core.runtime import NORYXRuntime
from core.sqlite_audit import SQLiteAuditLog

audit = SQLiteAuditLog("/var/lib/noryx7/audit.sqlite")
runtime = NORYXRuntime(audit_log=audit)
try:
    result = runtime.run(task)
finally:
    audit.close()
```

This is an injection point, not an automatic deployment policy. A hosted
deployment must explicitly configure the backend and place the database on a
persistent volume with appropriate filesystem permissions. Ephemeral container
storage does not provide durability across replacement or redeployment.
Remote authenticated checkpoints are still needed for database rollback
detection. The gateway's default runtime construction is not silently changed.
