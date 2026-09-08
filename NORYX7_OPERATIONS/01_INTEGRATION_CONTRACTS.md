# NORYX7 — Integration Contracts

## Purpose

This file is the integration reference for continuing development without rediscovering established contracts.

## JARVIS contracts

`Request(text, principal_id, request_id)`

`Plan(request_id, steps)`

`PlanStep(step_id, capability, target, parameters, dependencies)`

`ActionResult(step_id, success, output=None, error="")`

## JARVIS runtime flow

1. Validate Request and Plan types.
2. Ensure `plan.request_id == request.request_id`.
3. Require recovery state NORMAL.
4. Require a JARVIS Policy grant for every planned capability/target.
5. Reserve execution state.
6. Run through RecoveryController.
7. Bridge JARVIS Plan into RuntimeEngine steps.
8. Runtime builds action envelopes and invokes the executor.
9. Executor creates an ActionSpec and uses canonical authorization.
10. ToolExecutor resolves the capability from the shared canonical registry.
11. Handler executes.
12. Tool output is verified.
13. Runtime verifies/attests and returns outputs.
14. Bridge reconstructs JARVIS ActionResults.
15. JARVIS verifies result count/order/success.
16. StateStore commits verified results.

## Policy contract

`jarvis.core.policy.Policy` is thread-safe, bounded and deny-by-default.

A grant is exactly:

`(principal_id, capability, target)`

No matching grant means `authorize()` returns False.

`grant()` adds an explicit grant.

`revoke()` removes it.

Do not change this behavior to accommodate tests.

## Core authorization contract

`core.actions.ActionGate` is the canonical authorization boundary.

`AuthorizationAuthority` issues bounded authorization grants bound to action/execution identity and principal identity.

Auth-required execution must use the canonical linearized authorization path. Do not manually authorize and then authorize-and-execute the same one-shot grant.

## Registry contract

Canonical registry: `core.tools.CapabilityRegistry`.

JARVIS `jarvis.tools.registry.CapabilityRegistry` delegates to the core registry when constructed with `core_registry`.

JARVIS handler contract:

`handler(PlanStep) -> ActionResult`

Core handler contract:

`handler(target, dict(parameters))`

The JARVIS adapter performs the translation. Do not change the core handler contract.

## Runtime contract

`RuntimeResult` contains:

- execution_id
- status
- attestations
- outputs
- optional error

RuntimeEngine must receive the actual payload for digesting. A JARVIS `ActionResult` wrapper must not be passed into RuntimeEngine's output digest path.

## State contract

`JarvisState` stores execution/request/principal identity, request digest, completed steps, results and status.

At commit time `results` must be a list.

Verified execution results are committed with the expected execution/request/principal identity.

## Recovery contract

Recovery implementation is in `core/recovery.py`.

Execution uses a snapshot/epoch and `run_if_normal(..., expected_epoch=...)` to prevent authorization-to-execution TOCTOU across recovery state changes.

## HYPERSYNTH contract

Existing HYPERSYNTH execution rejection paths have explicit `execution_id` binding. This was already repaired and verified. Do not reapply that patch.

## Integration discipline

Never bypass a boundary just because it rejects an operation. A rejection must be classified as either:

- expected security behavior, or
- genuine integration defect.

Only the second category should result in a code patch.
