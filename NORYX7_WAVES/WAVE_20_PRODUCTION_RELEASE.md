# WAVE 20 — PRODUCTION HARDENING & RELEASE

Dependency: Wave 19 CLOSED.

## Goal
Certify NORYX7 for controlled production deployment with reproducible builds, safe configuration, rollback and operational recovery.

## Must verify
- production configuration is explicit and reproducible;
- secrets are injected only through approved runtime configuration;
- dependency versions and supply-chain checks are recorded;
- startup health is truthful;
- migrations are backward/forward safe where required;
- rollback is tested;
- graceful shutdown preserves state/audit invariants;
- deployment drift is detectable;
- security and authorization remain fail-closed in production mode.

## Closure tests
Clean deployment, restart, rollback, configuration omission, provider outage, state recovery, secret-redaction audit, dependency integrity, health/readiness semantics and full production E2E certification.
