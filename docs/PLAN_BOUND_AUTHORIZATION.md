# Plan-Bound Runtime Authorization

Status: implementation candidate in PR #16; CI not yet verified.

## Change

The runtime now computes a canonical digest of the complete scheduled plan. The digest includes each step ID, action type, target, parameters, sorted dependency IDs and risk class. Steps are sorted by ID before hashing so equivalent plans are stable under input ordering.

The plan digest is attached to every dispatched ActionEnvelope and included in:
- the concrete per-attempt action digest (which also includes the nonce);
- the stable authorization statement signed by approvers;
- the runtime attestation indirectly through its action digest and signature.

This closes a binding gap where two plans could contain an otherwise identical step action but different dependency relationships, while the previous per-step authorization statement did not identify the surrounding plan.

## Limits

- This binds the plan submitted to RuntimeEngine; it does not prove the planner selected a safe or optimal plan.
- The scheduler still needs stronger durable DAG state, retries, cancellation and uncertain-outcome recovery.
- This does not make caller-supplied result verifier callbacks independent or trusted.
- Existing external approval providers must sign the new statement including `plan_digest`; old proofs will not validate for the changed statement.
- The digest is not a substitute for validating dependency semantics or enforcing authorization at each external side-effect boundary.

No production deployment or CI result is claimed until the exact PR head completes all checks.
