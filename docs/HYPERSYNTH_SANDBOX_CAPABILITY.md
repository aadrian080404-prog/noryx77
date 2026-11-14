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

## Real Bubblewrap smoke test

The opt-in integration test `core/test_os_sandbox_e2e.py` exercises the actual
Bubblewrap runner rather than a fake adapter. On a Linux host with Bubblewrap
and unprivileged user namespaces enabled, run:

```sh
NORYX7_RUN_BWRAP_E2E=1 pytest -q core/test_os_sandbox_e2e.py
```

It verifies that a process can write through the supplied workspace, that an
outbound connection attempt fails inside the network namespace, and that the
configured CPU, address-space, file-size, descriptor, process-count and core
limits are effective inside the sandbox. The dedicated
`.github/workflows/bubblewrap-integration.yml` workflow installs Bubblewrap
and runs this test on a Linux CI host. A successful hosted-runner test is
evidence for that runner environment, not proof of the production host's
kernel configuration; deployments must still run it on their target host.

The runner also requires the Linux `prlimit` and `setpriv` utilities. CPU,
address-space, file-size, descriptor and core-dump limits are applied before
Bubblewrap. The process-count limit is deliberately applied by a second
`prlimit` invocation inside the new namespaces: applying `RLIMIT_NPROC`
before namespace creation can prevent Bubblewrap itself from creating the
namespace when the host user already has more processes than the requested
limit. `no_new_privs` is set through `setpriv` before starting Bubblewrap.
The runner deliberately avoids Python `preexec_fn` hooks, which are unsafe in
multithreaded parent processes. Missing utilities fail closed.
