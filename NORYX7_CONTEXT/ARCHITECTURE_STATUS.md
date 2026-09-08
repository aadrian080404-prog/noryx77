# NORYX7 — Architecture & Integration Status

## Purpose
NORYX7 is being developed as a distributed AI platform, not a simple chatbot. The architecture separates reasoning/planning from authorization, capability execution, runtime state, verification, recovery, and memory.

## Target architecture

USER
→ TEXT / VOICE / BROWSER / API
→ IDENTITY / SESSION
→ USER UNDERSTANDING
→ GLOBAL + LOCAL MEMORY
→ HYPERSYNTH
→ MODEL FABRIC
→ DECISION / PLAN
→ JARVIS / ORCHESTRATION
→ POLICY
→ AUTHORIZATION
→ CAPABILITY REGISTRY
→ TOOL EXECUTOR
→ RUNTIME ENGINE
→ VERIFICATION / ATTESTATION
→ STATE / AUDIT / RECOVERY
→ MEMORY
→ USER / TEXT / TTS

Not every request needs every subsystem. The unified orchestration layer should select the required path while execution remains bounded by policy, authorization, capabilities, runtime controls and verification.

## Current verified integration

### JARVIS → Core → Runtime vertical path
Verified end-to-end with an explicitly granted `compute` capability:

JARVIS Policy grant
→ JarvisRuntime.execute
→ RecoveryController
→ JarvisRuntimeBridge
→ RuntimeEngine
→ ActionGate
→ AuthorizationAuthority
→ ToolExecutor
→ shared CapabilityRegistry
→ JARVIS handler
→ Verification
→ Runtime attestation/state flow
→ JARVIS ActionResult
→ JarvisStateStore commit

Result: PASS.

### Shared capability registry
JARVIS CapabilityRegistry delegates to the canonical Core capability registry supplied by ToolExecutor. Registration made through JARVIS is visible to ToolExecutor.

Result: PASS.

### State contract
`JarvisStateStore.commit()` requires list-based `results`; the runtime path now passes `results=list(results)` before commit.

Result: PASS.

### Recovery
`core/recovery.py` uses state + epoch checks and `run_if_normal()` to prevent execution during recovery or across a changed recovery epoch.

Result: verified in prior integration work; no change required in current pass.

## Security status

The JARVIS policy is intentionally deny-by-default. A request is not executable merely because a model or planner produced it.

Policy grant binding is:
`(principal_id, capability, target)`.

Verified:
- no grant → deny
- explicit grant → allow
- revoke → deny
- revoked capability is blocked before handler invocation
- different capability does not inherit the grant
- different target does not inherit the grant
- different principal does not inherit the grant

Official authorization/security tests currently verified:
- `core/test_authorization_grants.py`: 12 passed
- `core/test_security_contracts.py`, `core/test_adversarial_boundaries.py`, `core/test_hypersynth_adversarial.py`: 45 passed

The security controls are not to be bypassed or weakened merely to make integration tests pass.

## Baseline from previous audit

- Full suite: 702 passed, 0 failures/errors
- Targeted integration: 61 passed
- Repository Python parse audit: PASS
- Forbidden `eval/exec/os.system/os.popen` audit: PASS
- Canonical import audit: PASS
- Intentional `NotImplementedError` contract preserved
- No code changes were made during the previous global audit

## Recent commits on working branch

Branch: `frontier-hardening-2026-09-07`

Recent commits:
- `6d171ef` feat(frontier): harden runtime invariants and lifecycle safety
- `8b1a723` Align replay rollback test with concurrent channel semantics
- `4fb7658` Restore bounded concurrent replay protection
- `663c08f` Fix remaining runtime, offline, and secure-channel contract failures
- `059917c` Add consolidated zero-failure compatibility repair v2

## Important completed fixes

### Runtime rejection identity
`core/runtime.py` was corrected so all 11 Hypersynth rejection paths bind `execution_id`.

Verification:
- rejection calls: 11
- missing execution_id: []
- rejection call binding: PASS

### Bridge output normalization
`core/jarvis_runtime_bridge.py` unwraps JARVIS `ActionResult.output` before returning to RuntimeEngine so RuntimeEngine digesting receives the actual payload rather than a JARVIS wrapper.

### JARVIS state commit
`jarvis/core/runtime.py` now converts bridge results to a list before constructing `JarvisState` for the StateStore contract.

Backup created during that repair:
`jarvis/core/runtime.py.bak_before_results_fix`

## Current conclusion

The JARVIS authorization/runtime integration block is VERIFIED. Do not repeatedly re-test or bypass this layer unless a new regression appears. Next work should connect the remaining architectural structures using their real repository contracts and existing tests.
