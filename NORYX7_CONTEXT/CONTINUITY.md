# NORYX7 — Continuity / Handoff

## Working branch
`frontier-hardening-2026-09-07`

## Repository
`adrianatlas03-coder/noryx7-`

## Working environment
Primary development environment used in this phase: Termux, project path `~/noryx7`.

## Current state
The repository has a mature security/runtime architecture and must be extended by integration, not by replacing components wholesale.

The JARVIS → Core → Runtime path is now verified with explicit policy authorization.

## Key contracts that must not be broken

### Core capability handler
Canonical Core registry handler contract:
`handler(target, dict(parameters))`

Do not change this contract.

### JARVIS capability compatibility
JARVIS tests may register handlers using:
`handler(PlanStep) -> ActionResult`

The JARVIS registry adapter translates this public JARVIS contract to the canonical Core registry contract.

### RuntimeResult
`RuntimeResult` contains:
- execution_id
- status
- attestations
- outputs
- error

RuntimeEngine should receive the actual output payload, not a JARVIS `ActionResult` wrapper.

### JarvisState
`JarvisState.results` is a list. Before StateStore commit, JARVIS runtime must supply a list.

### Authorization
Do not call `ActionGate.authorize()` separately before the auth-required `authorize_and_execute()` path when that would consume a one-shot grant twice.

JARVIS user-level policy is deny-by-default and requires explicit grants.

## Recent source changes already made

- `core/runtime.py`: fixed all 11 Hypersynth rejection paths to bind execution_id.
- `core/jarvis_runtime_bridge.py`: unwraps successful JARVIS `ActionResult` to its `.output` payload before RuntimeEngine digesting.
- `jarvis/tools/registry.py`: JARVIS registry delegates to canonical Core registry and adapts PlanStep handlers.
- `jarvis/core/runtime.py`: constructs `JarvisState` with `results=list(results)` for StateStore compatibility.

Do not reapply these patches.

## Backups in repository

Several historical backups exist under `jarvis/core/`, including:
- `runtime.py.pre_bridge`
- `runtime.py.pre_registry_unification`
- `runtime.py.pre_canonical_execute_v2`
- `runtime.py.pre_authorization_integration`
- `runtime.py.pre_request_digest`
- `runtime.py.bak_before_results_fix`

Treat them as historical references, not active source.

## Closed investigation
The earlier `capability_denied` vertical failure was caused by an empty JARVIS policy grant set. The policy was working correctly. After an explicit grant, the full vertical execution passed.

Do not bypass the policy to make integration tests pass.

## Next objective
Continue connecting remaining NORYX7 structures (Hypersynth, model fabric, orchestration, memory, tools, browser/API interfaces, verification/attestation, state/recovery and other runtime structures) using their existing contracts.

For each integration:
1. inspect the real implementation and existing tests;
2. identify the exact contract boundary;
3. implement the smallest compatible integration;
4. run targeted tests;
5. run relevant regression tests;
6. record the result in this context folder.

Do not invent parallel APIs when an existing repository interface can be reused.
