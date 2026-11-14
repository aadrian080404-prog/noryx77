# ExecutionFabric → Bubblewrap integration adapter

`SandboxedProcessAdapter` registers a narrow `sandboxed_process` environment
with the existing `ExecutionFabric`. The fabric's authorization callback is
evaluated before the adapter is invoked. The adapter accepts only
`action_type="process"`, `target="workspace"`, and one `argv` parameter.
It does not expose shell mode, inherited environment, network access, arbitrary
mounts, host targets or caller-selected limits.

The adapter delegates every accepted process action to
`BubblewrapSandboxRunner`; missing Bubblewrap or namespace support remains a
hard failure. Tests verify authorization denial never reaches the runner and
unsupported capabilities are rejected.

Integration boundary: this connects the ExecutionFabric abstraction to the
OS sandbox adapter, but it does not yet replace every existing application or
runtime execution path. A production rollout still requires a canonical
runtime entry point, syscall filtering (seccomp), filesystem restrictions
(Landlock), cgroup v2 resource enforcement, policy review and end-to-end tests.
