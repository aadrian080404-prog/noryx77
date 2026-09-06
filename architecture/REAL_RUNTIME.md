# NORYX7 — Real Runtime Architecture

This directory is the isolated design/implementation track for the operational NORYX7 system. It does not replace the hardened foundation while that foundation is still under adversarial verification.

## Goal

Turn NORYX7 from a cognitive-kernel prototype into an actual bounded operating system for agentic work: it receives an intent, establishes identity and authority, builds an execution plan, acquires only the required context, selects compute/tools, executes through a cryptographic action boundary, verifies every side effect, and commits only verified state.

## Runtime flow

```text
USER / EVENT
    |
    v
[Ingress + Identity]
    |
    v
[Intent Normalizer]
    |
    v
[Context / Memory Resolver] -----> [Policy + Trust]
    |
    v
[Planner]
    |
    v
[Plan Verifier]
    |
    v
[Resource Router]
    |
    v
[Capability Broker]
    |
    v
[Action Scheduler]
    |
    v
[Secure Dispatch]
    |
    +----> [Tool / Model / OS Adapter]
    |
    v
[Result Attestation]
    |
    v
[State Commit Gate]
    |
    +----> [Memory / Audit / Event Log]
    |
    v
[User-visible Result]
```

## Core runtime objects

- **Intent**: immutable user/event request with provenance.
- **ExecutionContext**: execution ID, principal, policy snapshot, deadlines and resource budget.
- **Plan**: typed DAG of bounded steps; no free-form execution.
- **Capability**: narrowly scoped authority for one operation/resource/target and execution.
- **ActionEnvelope**: canonical, signed description of the exact action to dispatch.
- **Attestation**: signed result binding action, execution, agent identity, output digest and verification state.
- **StateCommit**: atomic proposal to mutate NORYX7 state; commits only after verification.

## Design rule

Models propose. Verifiers decide. Capabilities authorize. Adapters execute. The state layer commits. No model output directly mutates trusted state.

## Runtime planes

### 1. Control plane
Identity, policy, capabilities, planning, scheduling, verification, revocation and audit.

### 2. Data plane
Model inference, tool calls, browser/network adapters, local OS adapters and external services.

### 3. State plane
Authoritative task state, memory, durable event log, checkpoints and recovery metadata.

The data plane is never trusted merely because the control plane requested work. Every crossing is authenticated and bound to the current execution context.

## First implementation stages

1. Typed runtime contracts and event model.
2. ExecutionContext and lifecycle state machine.
3. Capability broker with scoped, expiring, single-use grants.
4. Adapter interface for models/tools/OS operations.
5. Scheduler with deadlines, cancellation and bounded concurrency.
6. Result attestation and state-commit gate.
7. Durable journal and deterministic recovery.
8. Multi-agent/remote execution over the existing Secure Channel.

## Non-goals for this branch

- training a new frontier model;
- unrestricted autonomous access to the host;
- bypassing OS/browser permission systems;
- treating cryptography as a substitute for authorization or verification.
