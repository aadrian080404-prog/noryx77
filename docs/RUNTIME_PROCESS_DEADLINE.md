# Runtime deadline propagation to process executors

When the injected adapter exposes `execute_with_timeout(envelope, timeout_seconds)`, RuntimeEngine passes the remaining execution budget derived from its monotonic deadline. `ProcessExecutionAdapter` implements this optional bounded-execution method and terminates its child when the runtime budget expires, even if the adapter's configured default timeout is longer.

Adapters that expose only `execute` retain their own timeout semantics and cannot be forcibly interrupted by RuntimeEngine. The process adapter remains a killable process boundary, not an OS sandbox; a terminated process may already have caused external side effects and the durable runtime reservation must remain pending for reconciliation.
