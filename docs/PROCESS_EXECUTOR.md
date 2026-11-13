# Process-backed Runtime Executor

`noryx7_runtime.ProcessExecutionAdapter` runs a trusted, importable/picklable handler in a spawned child process. The parent enforces a deadline, terminates the child on timeout, escalates to kill if necessary, and accepts results only as bounded JSON bytes. Exception details are not returned; only the exception type crosses the process boundary.

The adapter satisfies the runtime execution-adapter contract and can be injected into `RuntimeEngine`.

## Security boundary and limits

This is a killable process boundary, not a security sandbox. The child runs with the same operating-system user privileges, filesystem access, environment and network access as the parent. Do not execute untrusted handlers with it. OS-level sandboxing, syscall filtering, resource quotas, cgroups/job objects, restricted credentials and network namespaces require a separately provisioned platform sandbox.

Handlers must be importable/picklable under Python's spawn start method. Results must be JSON serializable and remain below the configured byte limit. External side effects may still have occurred if a process is killed; the runtime journal must preserve a pending reservation and require reconciliation rather than blindly retrying.
