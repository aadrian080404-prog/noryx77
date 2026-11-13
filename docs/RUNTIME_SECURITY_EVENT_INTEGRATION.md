# Runtime Security Event Integration

The runtime can receive a `SecurityEventBus` and opt into `require_durable_security_events=True`. Strict mode rejects construction without a durable event sink and checks availability before high-risk authorization.

The runtime emits structured events for authorization failures, executor/process failures and verification failures. Event payloads contain only an evidence digest over execution/step/action identifiers and a bounded reason code; raw exception messages and action parameters are not written to the event stream. If event persistence fails while handling a failure, the runtime returns `security_event_persistence_failed` rather than pretending the event was recorded.

Use `core.DurableSecurityEventBus` for persistent local event history.

## Limits

The event sink is local and single-process. This is not remote SIEM integration, real-time alert delivery or automated containment. A durable event log is not proof that the source evidence is authentic. High-risk action audit is limited to the events emitted by this runtime path; other subsystems need their own event instrumentation.
