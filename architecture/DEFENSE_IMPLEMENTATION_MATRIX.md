# NORYX7 Defense Implementation Matrix

This is the implementation order for the defense-first build. Each row becomes a contract, implementation, integration test, adversarial campaign, and recovery test before being marked verified.

| Domain | Required control | Verification gate |
|---|---|---|
| Perimeter | Stateful ingress/egress policy, protocol filtering, rate limits, independent security events | deny-by-default, malformed traffic, burst limits, egress escape attempts |
| Zero Trust | Identity → authentication → authorization → context → policy → risk → allow/deny/isolate | identity swap, revoked identity, context mismatch, fail-closed |
| Identity/keys | Scoped identities, key separation, revocation, multi-party approval boundary | substitution, replay, revoked-key use, privilege escalation |
| Segmentation | Compute/memory/agents/tools/user-data/model/management/security zones | cross-zone access attempts, confused-deputy paths |
| Sandbox | Untrusted code isolation with bounded resources and no production trust | escape, resource exhaustion, secret/network access attempts |
| Adversarial engine | Deterministic generated scenarios with held-out cases | generalization, regression, adaptive attacks, compound attacks |
| Containment | Detect → classify → isolate → revoke → preserve evidence | simultaneous compromise and race conditions |
| Malware/EDR | Provenance, integrity, behavior and connection telemetry | unsigned/modified component, lateral movement, persistence |
| Supply chain | Verified dependencies, builds, images, firmware and updates | tampering, rollback, provenance mismatch |
| Boot/hardware trust | Verified boot chain and attested runtime boundary | altered image, stale measurement, trust-anchor mismatch |
| Immutable Core | Separate trust anchors, root policy and emergency controls from agent authority | attempted self-modification and privilege escalation |
| Recovery | Trusted-components-only restore from verified offline catalog | corrupted backup, rollback, partial recovery, repeated incident |
| Audit/forensics | Append-only tamper-evident evidence independent from monitored component | deletion, reordering, corruption, checkpoint mismatch |
| Distribution | Device/edge/cloud/offline compartmentalization | loss of one or more nodes without global trust collapse |
| Active defense | Isolation, revocation, evidence preservation, honeypot/deception where authorized | no unauthorized external offensive action; containment effectiveness |

## Global invariant

> A successful compromise of one component must not imply compromise of NORYX7's trusted state, root authorization, or unrelated components.

## Build discipline

1. Implement contracts and fail-closed semantics.
2. Integrate them into runtime control flow.
3. Add deterministic unit/property/fuzz/adversarial tests.
4. Run full regression and inspect failures.
5. Fix the root cause, not the individual failing case.
6. Repeat with higher difficulty and compound scenarios.
7. Only then mark the control verified.

Finite tests do not prove absence of arbitrary vulnerabilities. The long-term target is continuous generated evaluation at million-case scale, with held-out scenarios and independent verification.
