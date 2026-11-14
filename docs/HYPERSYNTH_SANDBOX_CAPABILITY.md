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

The canonical runtime currently constructs its `ActionGate` without an
`AuthorizationAuthority` injection point. Consequently, the registered
high-risk capability remains fail-closed and cannot yet be executed through
the public canonical constructor, even when an adapter is supplied. This PR
only proves registration and routing configuration; it does not make
production process execution operational. A follow-up must add a durable,
identity-registry-bound authorization authority before enabling that route.
