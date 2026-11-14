# Canonical Runtime — Sandbox Authorization Boundary

## Construction contract

The canonical runtime accepts an optional sandbox adapter, identity registry and
authorization authority. The sandbox capability is not registered by default.
When present, it is classified as high risk and remains behind ToolExecutor,
ActionGate and the existing authorization checks.

An injected authority is accepted only when all of the following hold:

- it is an `AuthorizationAuthority`;
- it references the exact same `IdentityRegistry` object injected into the runtime;
- it uses durable, integrity-protected replay storage;
- authenticated replay is mandatory.

The runtime does not silently replace a missing or invalid authority with a
weaker default. Without an authority, a high-risk sandbox action is denied
before the adapter is invoked.

## Dispatch and replay

The authorization grant is bound to the action and execution ID. A successful
dispatch consumes the grant; a subsequent replay must fail before a second
adapter invocation.

The regression suite covers both sequential replay and two simultaneous
threads submitting the same grant. The concurrent test requires exactly one
successful dispatch and exactly one adapter invocation.

The authority keeps its identity/replay critical section across the protected
dispatch so revocation cannot interleave between authorization and the side
effect. This is a deliberate safety barrier. Do not shorten or release this
critical section without preserving the revocation barrier and adding tests for
nested dispatch, same-thread revocation and failure recovery.

## What has and has not been demonstrated

- Unit/integration tests use a stub adapter to verify the runtime's identity,
  authorization, one-shot consumption and replay behavior.
- The dedicated Bubblewrap CI workflow separately exercises the real OS runner,
  network namespace, workspace boundary and effective resource limits.
- These two test groups do not yet constitute one end-to-end test in which a
  real authorization grant drives a real Bubblewrap process and the resulting
  process evidence is committed to the production audit backend.
- Production deployment still requires target-host validation, durable key
  provisioning, external anti-rollback protection, and an explicit policy for
  revocation and uncertain process outcomes.

A green CI result is evidence for the exact tested commit and test environment;
it is not a production security certification.
