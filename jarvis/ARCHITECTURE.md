# JARVIS architecture

```text
Request -> Identity -> Intent/Plan -> Policy -> Capability Registry -> Executor -> Result -> Audit
                         |                 |                    |
                         +---- bounded ----+---- explicit ------+
```

## Boundaries

- Models/providers produce proposals only.
- Plans are immutable and tied to one request ID.
- Policy is deny-by-default and grants principal + capability + target.
- Capabilities are explicitly registered; unknown capabilities fail closed.
- Executors return typed `ActionResult` values.
- Audit records start, success/failure and completion events.
- Memory is bounded and must remain behind a dedicated store interface.

## Security direction

Future OS/network/browser integrations must be adapters behind the same capability and authorization boundaries. Secrets must use an OS/KMS boundary rather than application source or plaintext configuration.
