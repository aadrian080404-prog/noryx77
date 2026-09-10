# WAVE 12 — EXTERNAL CAPABILITY FABRIC

Dependency: Wave 11 CLOSED.

## Goal
Turn external integrations into real, bounded capability adapters without creating privileged bypasses.

## Scope
Payments, travel/flights, insurance, commerce and future external services. Each adapter gets explicit credential ownership, capability registration, target binding, policy requirements, timeout, retry/idempotency and result verification.

## Must verify
- absent credentials → fail closed;
- wrong principal/capability/target → deny;
- secrets never enter model prompts, logs or memory;
- external result provenance and freshness are recorded;
- retries cannot duplicate irreversible actions;
- provider errors cannot be mistaken for successful execution;
- sandbox and production endpoints are distinct.

## Closure tests
Credential absence, revoked grant, replay, timeout, duplicate request, malformed provider result, provider compromise simulation, successful sandbox transaction and complete audit trail.
