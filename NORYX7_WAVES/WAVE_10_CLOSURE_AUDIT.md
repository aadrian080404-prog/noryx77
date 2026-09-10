# WAVE 10 — END-TO-END CLOSURE AUDIT

This document is the gate before Wave 11. It is an audit plan and finding register, not a claim that every item is fixed.

## A. Visible failure surface

1. Termux execution from the repository root must be the only local test baseline.
2. `/api/chat` must produce the same canonical execution semantics as `/v1/execute`; frontend wording must never mask a backend failure.
3. `/v1/health`, `/health`, `/api/models` and `/api/capabilities` must report one coherent provider/runtime state.
4. Browser online/offline state must reflect the actual gateway/runtime, not a secondary capability heuristic.
5. Mobile scrolling, input focus and result rendering must remain usable after repeated turns.
6. Hosted Render behavior must be tested separately from local behavior.

## B. Hidden seam audit

### Identity
- trace principal/session/client/task/execution IDs across every boundary;
- reject stale or cross-request IDs;
- confirm model/agent/tool results cannot overwrite execution identity;
- verify official creator identity is sourced from canonical identity data.

### Authorization/security
- inspect every execution path for ActionGate/policy bypasses;
- verify deny-by-default for unconfigured capabilities;
- check replay identity and replay windows;
- test revocation during execution;
- inspect external/egress boundaries for hidden network paths.

### Runtime/state
- verify direct runtime and gateway runtime use compatible lifecycle records;
- verify recovery blocks execution before cognition where required;
- verify state journal restore/commit symmetry;
- verify shutdown/restart does not create stale authority;
- verify all result containers satisfy downstream contracts.

### Model Fabric
- verify the adapter actually selected by routing is the adapter reported to the caller;
- verify provider/model configuration is consistent across API, health and runtime;
- verify unavailable providers fail closed rather than silently falling back;
- verify execution metadata belongs to the current execution.

### Agent Fabric/JARVIS
- verify agent registration reaches the canonical registry used at execution;
- verify JARVIS remains behind authorization and recovery;
- inspect optional configuration paths for accidental dead ends;
- verify secondary-agent participation is real when requested, not merely declared.

### HYPERSYNTH
- trace the actual runtime through perception, contracts, context, decomposition, planning, hypothesis, simulation, allocation, gate, execution, result admission, verification, consensus, output verification, metacognition, memory and audit;
- identify stages represented only as metadata or documentation;
- identify stages that can be skipped without an explicit contract reason.

### Memory/persistence
- verify memory writes are actually invoked by the canonical path;
- verify execution/principal binding on reads and writes;
- verify persistence survives restart;
- verify suspended/distributed memory does not silently become permanent storage.

### Web research/offline
- verify relevance filtering and current-execution metadata binding;
- verify no unrelated source is admitted as evidence;
- verify offline mode cannot imply current web knowledge;
- verify network access remains inside the egress boundary.

### Voice/vision
- verify canonical boundaries exist and are connected to runtime;
- verify hosted web does not advertise unimplemented microphone/STT/TTS/vision features;
- test malformed media and capability denial.

### Ecosystem
- compare declared architecture matrix against executable imports/call graph;
- detect duplicate implementations of the same contract;
- detect compatibility shims that silently replace canonical components;
- detect dead adapters, unused registries and untraversed routes.

## C. Code-search indicators

Current repository inspection found intentional abstract contracts using `NotImplementedError` in agent, attestation and key-provider interfaces; these are not automatically bugs and must be distinguished from production paths. The repository also contains explicit no-op/default compatibility handlers, so audit must determine whether each is declarative-only or reachable during real execution.

The architecture status itself states that the JARVIS/Core/Runtime vertical path is verified and that remaining structures should be connected through real repository contracts. fileciteturn7file0L2-L2

## D. Closure rule

No item is closed because a symbol exists, an endpoint returns JSON, or a unit test passes in isolation. An item closes only when the real caller traverses the real boundary and the result is verified with the correct identity, policy, provenance and state.

Final Wave 10 gate:
`python -m pytest core noryx7_runtime ecosystem jarvis tests -q` → exit code 0.
Then compileall + local E2E + hosted E2E + semantic cases + browser verification.
