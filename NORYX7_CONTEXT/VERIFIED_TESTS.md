# NORYX7 — Verified Tests & Evidence

This file records verified results from the current integration session so future work does not repeat already-closed investigations.

## Security / authorization

### JARVIS policy deny-by-default
Observed on a fresh `JarvisRuntime`:
- `Policy.authorize(principal-1, compute, integration)` returned `False`
- `_grants` was empty

This was correct behavior, not a defect.

### Explicit JARVIS grant + vertical execution
After:
`runtime.grant("principal-1", "compute", "integration")`

Observed:
- `POLICY_AFTER_GRANT: True`
- one successful `ActionResult`
- handler actually called
- state exists
- state status: `committed`
- sequence: `1`
- `VERTICAL JARVIS RUNTIME: PASS`
- `STATE COMMIT: PASS`

### Grant / revoke
Observed:
- `BEFORE: False`
- `AFTER_GRANT: True`
- `AFTER_REVOKE: False`
- `POLICY GRANT/REVOKE: PASS`
- `DENY-BY-DEFAULT: PASS`

### Runtime revocation enforcement
After granting and then revoking `compute + integration`:
- `AUTHORIZED_BEFORE_REVOKE: True`
- `AUTHORIZED_AFTER_REVOKE: False`
- execution raised `PermissionError capability_denied`
- `HANDLER_CALLED: []`
- `REVOKED EXECUTION BLOCKED: PASS`
- `RUNTIME REVOCATION ENFORCEMENT: PASS`

### Authorization binding / isolation
A grant for `(principal-integrity-test, compute, integration)` produced:
- original: `True`
- different capability: `False`
- different target: `False`
- different principal: `False`

Results:
- `AUTHORIZATION BINDING: PASS`
- `CAPABILITY ISOLATION: PASS`
- `TARGET ISOLATION: PASS`
- `PRINCIPAL ISOLATION: PASS`

### Official authorization grant suite
Command:
`pytest -q core/test_authorization_grants.py`

Result:
`12 passed in 0.54s`

### Official security/adversarial suites
Command:
`pytest -q core/test_security_contracts.py core/test_adversarial_boundaries.py core/test_hypersynth_adversarial.py`

Result:
`45 passed in 0.96s`

## Previously verified bridge path
Direct vertical bridge test produced:
`ActionResult(step_id='step-1', success=True, output={'ok': True, 'source': 'jarvis'})`

Full bridge diagnostic produced a tuple containing a successful JARVIS `ActionResult`; `_verify_results()` returned `True`.

## Baseline

Previous full regression baseline:
`702 passed in ~23s, 0 failures/errors`

Previous targeted integration baseline:
`61 passed`

## Testing rule

Do not weaken policy, authorization, runtime, recovery, verification, or adversarial tests to obtain a green result. First identify the violated contract, then make the smallest compatible change, run the targeted test, and finally run relevant regression tests.

Do not invent APIs for new tests when repository tests already cover the contract. Inspect/use the actual implementation and existing test interfaces.
