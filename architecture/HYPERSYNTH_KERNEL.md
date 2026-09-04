# HYPERSYNTH CORE

HYPERSYNTH is the bounded cognitive kernel inside NORYX7, not the Browser and not JARVIS.

## Operational pipeline

1. **Perception** — validate the task contract and execution identity.
2. **Context** — construct bounded context from task input and scoped memory.
3. **Planning** — produce and verify an immutable plan with bounded steps.
4. **Hypothesis** — generate candidate reasoning paths and verify structure.
5. **Simulation** — evaluate hypotheses before execution.
6. **Allocation** — select trusted agents/models and bind them to the same execution.
7. **Execution** — pass through policy/security/action gates; no model output bypasses authorization.
8. **Verification** — verify agent result, model request/result digests and identity binding.
9. **Metacognition** — reflect on confidence/quality within bounded result contracts.

## Trust invariant

The cognitive kernel may propose actions and model outputs, but it cannot directly commit trusted state. Authorization, cryptographic verification and state admission remain separate boundaries.

## Model Fabric binding

Model requests and results carry runtime and execution identity. Result envelopes bind request digest, selected model, candidate provenance/economics, output digest, confidence/degraded state and integrity MAC. HYPERSYNTH verifies this binding before provenance/state admission.

## Failure semantics

Malformed contracts, identity mismatch, policy denial, unavailable agents, model integrity failures, provenance failures and verifier exceptions fail closed. Bounded limits are enforced before dispatch.
