# NORYX7 — PowerShell & Cloud Terminal Fabric

## Purpose

Provide a secure, model-independent terminal plane inspired by the useful capabilities of PowerShell and browser-accessible Cloud Shell environments, while keeping execution behind NORYX7 policy, identity, sandbox and audit boundaries.

PowerShell is a cross-platform shell, scripting language and automation platform with object-based pipelines, history, completion/prediction and help. PowerShell 7+ supports cross-platform operation and SSH remoting; PowerShell jobs provide local background, thread and remote execution modes. These capabilities are incorporated as contracts, not as a privileged bypass. 

Cloud Shell patterns incorporated here include browser-accessible authenticated sessions, Bash/PowerShell selection, ephemeral sessions, optional persistent home storage, preconfigured developer/cloud tooling, editor integration and controlled web preview. Persistent storage and authentication are explicitly separated from the ephemeral compute host.

## 1. Terminal abstraction

`TerminalSession` represents an interactive execution context with:

- session identity;
- device identity;
- user/agent identity;
- shell type (`powershell`, `bash`, future shells);
- working directory;
- environment contract;
- capability grants;
- resource budget;
- network/egress policy;
- timeout/deadline;
- audit stream;
- persistence mode (`ephemeral`, `persistent`);
- trust/attestation state.

The terminal is not itself an authority. It receives capabilities from the NORYX7 control plane.

## 2. PowerShell capability fabric

Expose a PowerShell-compatible execution adapter where the host supports PowerShell 7+.

Capabilities to support:

- object-oriented pipeline semantics;
- command discovery;
- aliases and parameters;
- command history;
- completion/prediction;
- help/documentation;
- scripts and modules;
- background/thread/remote jobs;
- structured output capture;
- process/service/file/network inspection;
- cross-platform operation;
- SSH remoting;
- WSMan/Windows remoting where available;
- constrained/JEA-style role boundaries;
- secret-management adapter;
- transcript/audit integration.

NORYX7 must never silently elevate a PowerShell session. A command requiring a capability not present in the session is denied before execution.

## 3. Secure execution modes

### Local sandbox

For ordinary commands and scripts:

`COMMAND → POLICY → SANDBOX → EXECUTE → OBSERVE → RESULT → AUDIT`

### Background job

`SUBMIT → RESOURCE ADMISSION → JOB ISOLATION → EXECUTE → COLLECT → VERIFY → RELEASE`

### Remote job

`TARGET ATTESTATION → SESSION AUTH → CAPABILITY GRANT → REMOTE EXECUTION → RESULT VALIDATION → SESSION CLOSE`

### High-risk command

`PARSE → RISK CLASSIFY → HUMAN/POLICY AUTHORIZATION → ISOLATED EXECUTION → VERIFY → AUDIT`

No shell parser is allowed to bypass the authorization layer.

## 4. Remoting fabric

PowerShell 7+ SSH remoting is treated as one transport option. Other transports can be implemented behind the same contract.

`RemoteEndpoint` includes:

- endpoint identity;
- device identity;
- platform;
- transport;
- attestation status;
- host-key/fingerprint binding;
- session epoch;
- capability scope;
- expiry;
- network policy.

The endpoint must be independently revocable.

## 5. Cloud Terminal

NORYX7's Cloud Terminal is a generic cloud-session abstraction, not an Azure-only feature.

Supported conceptual modes:

- ephemeral cloud shell;
- persistent home/workspace;
- PowerShell shell;
- Bash shell;
- preconfigured tool environment;
- browser terminal UI;
- browser editor;
- controlled web preview;
- remote repository access;
- containerized workloads;
- CI/build environments.

The compute host is disposable. Persistent data lives in a separately authorized storage plane.

`CLOUD SESSION → EPHEMERAL COMPUTE`

`PERSISTENT DATA → SEPARATE STORAGE → ENCRYPTION → POLICY → AUDIT`

This prevents compromise of a terminal host from automatically becoming compromise of persistent NORYX7 state.

## 6. Tool environment

The terminal environment can expose approved tools such as:

- Git/GitHub CLI;
- Python;
- Node.js;
- Java/.NET;
- package managers;
- Docker/container tooling;
- Kubernetes tooling;
- Terraform/Ansible;
- database clients;
- compilers/build tools;
- PowerShell modules;
- cloud provider CLIs.

Tool installation is policy-controlled and provenance-checked. Untrusted packages are quarantined before admission.

## 7. Terminal object pipeline

When PowerShell is used, structured objects should remain structured across the NORYX7 adapter boundary where possible. Serialization is performed only at explicit transport boundaries.

This is important for latency and type fidelity: thread-local execution can avoid unnecessary serialization, while isolated/background/remote execution deliberately accepts serialization overhead for stronger isolation.

## 8. Performance fabric

The terminal scheduler chooses execution mode based on:

- latency target;
- isolation requirement;
- workload size;
- serialization cost;
- CPU/memory availability;
- network distance;
- privacy;
- risk.

Small local operations should not be sent to a remote/cloud job unnecessarily.

Independent commands may run concurrently under a bounded concurrency budget. Resource exhaustion is fail-closed.

## 9. Security boundaries

Terminal sessions cannot directly access:

- immutable Core;
- root trust anchors;
- global private keys;
- unrestricted memory stores;
- security-policy mutation;
- recovery authority;
- update signing authority;
- other users' credentials.

Secrets are injected only through a scoped secret provider and are never placed into normal model context unless explicitly authorized by policy.

PowerShell security controls should include the equivalent architectural concepts of application control, restricted remoting sessions, JEA-style least privilege, auditing and secret-management integration.

## 10. Web preview

Cloud-terminal web preview exposes only explicitly authorized ports/services.

`PORT REQUEST → POLICY → LOCAL BIND CHECK → AUTHENTICATED PREVIEW → EXPIRY → CLOSE`

No arbitrary public exposure is permitted.

## 11. Persistence

Two modes:

### Ephemeral

Session state disappears when the terminal ends.

### Persistent

Only explicitly selected workspace/home data survives. Persistent storage has its own identity, encryption, integrity and authorization boundary.

## 12. NORYX7 integration

HYPERSYNTH may reason about terminal operations, generate plans and interpret results, but the terminal remains a capability-gated executor.

`HYPERSYNTH → PLAN`

`CONTROL PLANE → AUTHORIZE`

`TERMINAL FABRIC → EXECUTE`

`OBSERVABILITY → CAPTURE`

`VERIFICATION → ACCEPT/REJECT`

This prevents the AI from becoming an implicit shell root.

## 13. Browser boundary

NORYX Browser v0.1 remains a standalone browser and does not embed this terminal or AI fabric. Future versions may expose a terminal UI through an explicit adapter after the browser/runtime security contract is defined.

## 14. Verification targets

Before this fabric is considered production-complete, verification must cover:

- command parsing and injection resistance;
- capability enforcement;
- sandbox escape resistance;
- local/background/thread/remote isolation;
- SSH host identity binding;
- session replay resistance;
- timeout/cancellation;
- resource exhaustion;
- secret leakage;
- persistent-storage isolation;
- package/provenance admission;
- web-preview exposure;
- audit completeness;
- failure recovery;
- cross-platform behavior;
- latency and concurrency under load.
