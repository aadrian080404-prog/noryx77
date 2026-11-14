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
