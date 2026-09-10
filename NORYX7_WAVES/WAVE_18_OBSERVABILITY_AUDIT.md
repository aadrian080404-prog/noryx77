# WAVE 18 — OBSERVABILITY, AUDIT & VERIFICATION

Dependency: Wave 17 CLOSED.

## Goal
Create one trustworthy execution trace from input to final result without leaking secrets or inventing evidence.

## Must verify
- task/execution/session/principal IDs correlate across all layers;
- provenance is complete for model, tool, agent, resource and external results;
- security decisions are auditable;
- audit records are tamper-evident;
- logs exclude credentials and sensitive payloads;
- verification failures are distinguishable from transport failures;
- metrics cannot become an authorization side channel.

## Closure tests
Full trace reconstruction, missing-event detection, digest tampering, secret-redaction tests, concurrent traces and failed execution diagnosis.
