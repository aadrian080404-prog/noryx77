# Canonical HYPERSYNTH sandbox capability

`HypersynthRuntime` accepts an optional `sandboxed_process_adapter`.
When supplied, it registers a `sandboxed_process` ToolExecutor capability with
risk class `high`. Calls still pass through the existing ToolExecutor and
ActionGate. High-risk execution requires the normal execution-bound
authorization grant and trusted principal; the adapter cannot be invoked by
simply registering a handler.

The adapter is intentionally narrow: the handler requires an action ID and
forwards the target and argv parameters to `SandboxedProcessAdapter`, which
accepts only the `workspace` target and a single `argv` parameter. No shell,
environment injection, network, mount, or arbitrary host path is exposed.

The capability is **not enabled by default**. A deployment must explicitly
construct the OS sandbox runner and workspace and inject the adapter into
`HypersynthRuntime`. Missing Bubblewrap or invalid sandbox setup must remain
fail-closed. This PR does not claim that every other runtime capability or
legacy code path is sandboxed; it adds one explicit high-risk route to the
canonical tool boundary.

Example:

```python
from core.hypersynth_runtime import HypersynthRuntime
from core.os_sandbox import BubblewrapRunner
from core.sandboxed_execution import SandboxedProcessAdapter

runner = BubblewrapRunner()
adapter = SandboxedProcessAdapter(runner, workspace="/var/lib/noryx7/workspace")
runtime = HypersynthRuntime(sandboxed_process_adapter=adapter)
```

Production deployment still needs OS-level verification of Bubblewrap,
kernel namespaces, filesystem permissions, resource limits and the host's
security policy. This PR does not add seccomp, Landlock, or cgroups.


## Canonical runtime injection

`NORYXRuntime` and `OperationalNORYXRuntime` expose an explicit
`sandboxed_process_adapter` injection point and pass it into
`HypersynthRuntime`. This makes the opt-in capability configurable at the
canonical runtime construction boundary. It remains disabled when no adapter
is supplied; no automatic Bubblewrap runner or workspace is created, and this
does not claim that unrelated legacy or external execution paths are sandboxed.

## Durable authorization at the canonical runtime boundary

The canonical `NORYXRuntime` and `OperationalNORYXRuntime` can now receive
an explicit `identity_registry` and `authorization_authority`. The authority
must reference the exact same registry object and must use a live,
file-backed `AuthenticatedAuthorizationReplayGuard` with
`require_authenticated_replay=True`. Ephemeral replay storage, unauthenticated
SQLite replay storage, a mismatched registry, or a closed authority is
rejected or remains fail-closed.

The runtime does not generate or persist authorization secrets, integrity
keys, replay database paths, Bubblewrap configuration, or workspaces on behalf
of a deployment. Operators must provision and protect these independently.
When no authority is supplied, the high-risk sandbox capability may be
registered by explicit adapter injection but cannot pass the authorization
gate. This is deliberate: adapter registration is not execution permission.

The externally supplied registry must be the registry used by the runtime;
the runtime adds its own deterministic-agent identity during construction.
A deployment should create a fresh registry for each runtime trust domain and
must not reuse a registry that already contains the reserved
`deterministic` identity.
