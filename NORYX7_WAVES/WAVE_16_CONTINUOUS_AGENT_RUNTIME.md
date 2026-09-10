# WAVE 16 — CONTINUOUS AGENT RUNTIME

Dependency: Wave 15 CLOSED.

## Goal
Connect long-lived agent execution, scheduling, supervision, bounded learning and recovery to the same authorization/runtime contract.

## Must verify
- no autonomous loop escapes action budgets;
- every scheduled action has a principal and policy context;
- supervisor can stop/revoke execution;
- state checkpoints are recoverable and replay-safe;
- learning updates cannot rewrite security policy;
- primary/secondary agents retain distinct but compatible roles;
- crashed agents cannot resume with stale authority.

## Closure tests
Start/stop/resume, crash recovery, revocation during execution, repeated scheduling, budget exhaustion, concurrent agents, stale checkpoint and adversarial self-modification attempts.
