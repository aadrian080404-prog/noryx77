# Linux OS sandbox boundary

## What this adds

`core.os_sandbox.BubblewrapSandboxRunner` is an execution adapter, not a claim
that the existing `core.sandbox.Sandbox` state machine already isolates code.
It requires Linux and an installed, executable Bubblewrap binary.

The runner:
- creates user, PID, network, IPC and UTS namespaces;
- exposes the system runtime directories read-only and only the supplied
  workspace as writable;
- provides isolated `/proc`, `/dev` and temporary storage;
- clears the child environment and closes unrelated file descriptors;
- never invokes a shell;
- applies CPU, address-space, file-size, descriptor, process-count and core
  dump limits before executing Bubblewrap;
- applies `PR_SET_NO_NEW_PRIVS`;
- enforces a wall-clock timeout and bounds captured output;
- fails closed if Linux, Bubblewrap or namespace creation is unavailable.

## Important boundary

This is a meaningful OS isolation layer, but it is not a complete production
container security profile. It does not configure cgroup v2 quotas, seccomp,
Landlock, SELinux/AppArmor policy, a dedicated unprivileged host account,
immutable image provenance, or an independently managed secrets broker.
The caller must stage only approved input into the workspace and must never
mount host credentials or sockets there. Production deployment requires
host-level hardening and adversarial integration tests on the target kernel.

No fallback to the host process executor is permitted when this runner fails.
