# Audited ExecutionFabric

`AuditedExecutionFabric` decorates the deny-by-default ExecutionFabric with
intent/outcome records in the authenticated hash-chained AuditLog. It hashes
canonical action parameters and records only the digest plus bounded routing
metadata; it does not copy parameter values, credentials or execution output.

The intent record is committed before authorization/execution. If that append
fails, the protected action is not invoked. Authorization or adapter failures
are recorded and re-raised. A successful action is followed by a completion
record; if that final append fails, the action has already happened and the
wrapper raises `execution_completed_but_audit_commit_failed`. The durable
intent remains, so the caller must treat the result as unknown and reconcile.

Important limitation: AuditLog is an in-memory hash chain in this repository
version. This decorator provides tamper-evident process-local evidence, not
durable crash-safe audit storage or external anti-rollback. Production must
connect it to independently persisted, checkpointed audit storage.
