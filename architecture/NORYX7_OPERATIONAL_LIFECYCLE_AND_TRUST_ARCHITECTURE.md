# NORYX7 — Operational lifecycle, trust domains and service continuity

**Status:** proposed architecture contract; source reconciliation required  
**Scope:** cross-cutting lifecycle for all 18 planes and deployment surfaces  
**Authority:** Identity, Policy, Capability Registry and ActionGate remain canonical; this document introduces no new authorization authority.

## 1. Purpose

A system architecture is incomplete if it describes only the successful request path. NORYX7 must define how it is created, provisioned, operated, updated, degraded, recovered, migrated and retired across local, device, edge, cloud, federated and offline environments.

This document specifies the lifecycle view for reconciliation with runtime, security, recovery, distribution, JARVIS, Browser and ecosystem sources. It does not claim those lifecycle functions already exist.

## 2. Trust and failure domains

- **Z0 Root of trust:** separately governed bootstrap anchors, release verification roots and emergency recovery policy.
- **Z1 Device boundary:** OS account, secure storage, device identity, local secrets, sensor/actuator access and user presence.
- **Z2 NORYX7 control plane:** identity, policy, capability, ActionGate, configuration governance and audit control.
- **Z3 Execution plane:** cognitive runtime, agent workers, tool adapters, sandbox and bounded action executors.
- **Z4 Data plane:** context, memory, journals, evidence, domain state, caches and replicas.
- **Z5 External/federated zone:** providers, remote agents, peer nodes, third-party APIs and independently operated services.
- **Z6 Physical/environmental zone:** people, sites, machines, sensors, energy systems and other real-world entities.

Trust does not automatically flow between zones. Every crossing needs explicit protocol, authenticated identities, permitted data classes, authority checks, bounded payloads, replay protection and auditable outcomes. A remote provider response is untrusted input even when the provider is authenticated.

## 3. Lifecycle state model

Each deployable service, agent, device, tenant and trust anchor has its own typed lifecycle; do not reuse one generic status field for unrelated state machines.

Stages:
1. DISCOVERED — known but not trusted.
2. ENROLLED — ownership and provenance evidence collected.
3. PROVISIONED — identity, policy and configuration installed.
4. ATTESTED — required posture evidence current and accepted.
5. READY — dependencies, capacity and policy permit bounded service.
6. ACTIVE — serving authorized work.
7. DEGRADED — safe reduced capability with explicit reason and review/expiry.
8. QUARANTINED — isolated pending investigation.
9. DRAINING — no new work; in-flight work follows explicit completion/cancel rules.
10. SUSPENDED — inactive but recoverable under policy.
11. REVOKED — trust or authority withdrawn; cannot be silently restored.
12. RETIRED — permanently decommissioned, with data/key disposition recorded.

Transitions require a named authority, preconditions, event evidence and failure result. REVOKED and RETIRED are not synonyms for temporary outage.

## 4. Bootstrap and first-run trust

Bootstrap is a privileged lifecycle, not an ordinary agent task.

Required sequence:
- establish device/installation identity and ownership claim;
- verify installation artifact and release provenance;
- establish/import a root trust anchor through a documented out-of-band or platform-protected procedure;
- enroll the initial human principal with explicit recovery factors;
- bind service identities and devices to principals under a single-owner or explicit multi-owner policy;
- provision least-privilege service capabilities;
- install initial policy/configuration with version and rollback metadata;
- initialize audit continuity and state-journal genesis;
- verify no privileged service starts in an untrusted or ambiguous state.

Bootstrap recovery must not create a backdoor or allow an agent to mint a replacement root of trust. Lost-root recovery requires a separately governed ceremony, evidence and audit trail.

## 5. Identity, key and cryptographic lifecycle

The repository contains multiple cryptographic primitives and trust components. Reconcile them as one lifecycle without pretending they are one mechanism.

Separate:
- identity key, encryption key, MAC key and attestation key;
- long-term root, intermediate/service and session keys;
- signing, key agreement, encryption, derivation, MAC and digest;
- key metadata versus secret key material;
- software keystore, OS-backed secure storage and HSM/KMS;
- cryptographic verification versus authorization decision.

Required key states: GENERATED, PENDING_ACTIVATION, ACTIVE, RETIRING, REVOKED, DESTROYED, COMPROMISED, UNKNOWN. Every key record binds algorithm, purpose, owner, scope, creation/activation/expiry, version, custody provider, rotation lineage and revocation status. Secret material never belongs in ordinary metadata stores or logs.

Rotation must cover overlap windows, historical verification, new signing, in-flight jobs, offline nodes, compromise, lost acknowledgement, KMS outage and recovery. An offline node cannot claim instantaneous global revocation without a communication path. High-risk actions fail closed when required freshness cannot be established.

Cryptographic agility is mandatory:
- algorithm and protocol identifiers are versioned, never inferred from key length;
- migration supports dual-read/controlled dual-sign only where policy permits;
- downgrade is prohibited unless explicitly approved and logged;
- deprecation and emergency replacement have governed rollout;
- post-quantum transition is separate from mathematical conjectures or primality testing;
- a library exposing an algorithm is not evidence that the algorithm is approved or secure.

## 6. Configuration, policy and schema lifecycle

Configuration, policy and schema are distinct artifacts with independent versioning.

Each release identifies immutable artifact digest/provenance, schema and canonicalization versions, policy version/authority, compatible runtime range, migrations, feature flags and safe defaults, secret references (never values), rollback compatibility and minimum supported predecessor.

Configuration precedence must be deterministic and inspectable: built-in defaults, installation profile, administrator policy, tenant policy, user preference. A lower authority cannot override a higher authority. Invalid or conflicting security-critical configuration yields safe refusal or reduced mode, not permissive defaults.

## 7. Upgrade, rollback and decommission

Upgrade is a controlled transaction across binaries, schemas, models, policies, keys and data.

Lifecycle: PROPOSED → REVIEWED → SIGNED → STAGED → PRECHECKED → CANARY → EXPANDED → ACCEPTED, with REJECTED, PAUSED, ROLLED_BACK and QUARANTINED alternatives.

Prechecks include signature/provenance, compatibility, capacity, backup/checkpoint health, key availability, policy compatibility, migration reversibility and recovery path. Rollback must not silently roll back revocations, audit history, financial ledgers or irreversible external effects.

Decommission requires stopping new admission, draining/cancelling bounded work, revoking identities/credentials/leases/capabilities, preserving required evidence without unnecessary personal data, deleting or cryptographically erasing eligible data/replicas, terminating external resources, removing discovery registrations and recording final artifact/key/data disposition.

## 8. Availability, partition and offline contract

Availability modes are explicit profiles:
- CONNECTED: required online authorities/dependencies reachable.
- CONSTRAINED: some providers/peers unavailable; bounded local functions remain.
- OFFLINE: only locally verifiable identities, policies, data and capabilities may be used.
- PARTITIONED_FEDERATION: local operation only within declared lease, scope and stale-state policy.
- RECOVERY: reconciliation and trust re-establishment before full service.

Every offline capability declares maximum offline duration; policy/key/revocation freshness; permitted/prohibited actions; local resource cap; queue retention; conflict strategy; replay defense; synchronization protocol; expiry behavior. No offline node invents global ordering or claims a remote commit it cannot observe.

For external side effects distinguish NOT_SENT, SENT_UNCONFIRMED, CONFIRMED, REJECTED, COMPENSATION_REQUIRED and INDETERMINATE. If the remote party may have acted but acknowledgement is missing, preserve indeterminate state and reconcile by idempotency key or authoritative query; never report a rollback that did not occur.

## 9. Backup, restore and disaster recovery

Classify backups by configuration/policy; identity/key metadata and separately protected secret material; state/domain records; execution journals/audit chains; memory/user content; evidence/provenance; model/agent manifests and signed artifacts.

Each class defines RPO, RTO, encryption, key dependency, retention, immutable/offline copy, integrity validation, restore ordering and deletion obligations. A readable backup is not necessarily trusted: restore verifies signatures, hashes, schema, authority epoch and audit continuity.

Recovery re-establishes trust roots and policy before privileged workloads. Restoring stale data must not resurrect revoked principals, replayed grants, retired keys or obsolete policy. Cross-store recovery requires a consistent recovery point or explicit reconciliation.

## 10. Observability, audit and incident response

Keep four channels distinct:
- operational telemetry (health, latency, resource use);
- security events (authentication, policy, revocation, anomaly);
- tamper-evident audit (who authorized/attempted/committed what);
- evidence/provenance (why a claim or result is trusted).

Each has access, retention, integrity and privacy rules. Logs must not leak secrets, raw private content or key material. Correlation IDs enable traceability but are not authority tokens.

Incident lifecycle: DETECT → TRIAGE → CONTAIN → PRESERVE_EVIDENCE → ERADICATE → RECOVER → REVIEW. Containment may quarantine an agent, node, key, artifact, provider or tenant. Evidence preservation must not block emergency revocation. Recovery requires independent re-attestation and explicit clearance. Post-incident review feeds architecture decisions, not silent policy edits.

## 11. Human operations and emergency control

Separate user, tenant administrator, system operator, security responder, auditor, domain expert and recovery custodian roles. No role implicitly receives every permission.

Emergency stop prevents new dispatch and revokes active capabilities within declared authority; it does not erase evidence or falsely claim external actions were undone. It needs an independently activatable path in the future implementation phase, controlled reset and post-event review.

Break-glass access is time-bound, scoped, visibly indicated, audited and dual-controlled where impact warrants. It cannot bypass cryptographic verification or rewrite audit history.

## 12. Service continuity and degradation

Every service declares criticality tier, dependencies, readiness/liveness, maximum queue depth/concurrency/retries/execution time, tenant/global budgets, circuit-breaker/backpressure behavior, safe degraded capability, recovery threshold and data-loss/consistency expectations.

A model/provider outage must not cause a different provider to inherit privileged context or permissions automatically. Failover re-evaluates data residency, trust, capability, cost and policy. Degraded service communicates reduced guarantees and never silently lowers verification or safety thresholds.

## 13. Lifecycle ownership matrix

| Concern | Logical owner | Supporting planes |
|---|---|---|
| Principal/device enrollment | Identity/Trust Authority | P07, P11, P13 |
| Policy/capability issuance | Policy/Capability Authority | P07, P11, P10 |
| Action admission/dispatch | ActionGate / Runtime authority | P08, P10, P15 |
| Key custody/cryptographic verification | Security/Key authority | P11, P13, P15 |
| State commit/recovery | State Authority | P12, P16, P15 |
| Data purpose/retention/deletion | Data governance authority | P02, P09, P12, P13, P14 |
| Release provenance/rollout | Supply-chain/release authority | P10, P11, P13, P16 |
| Resource quota/placement | Resource authority | P05, P10, P17 |
| Incident command/quarantine | Security operations authority | P11, P15, P16 |
| Domain escalation | Domain policy + qualified human | P18 and relevant domain planes |

This is logical ownership, not a claim that each authority currently exists as one service.

## 14. Open decisions before freeze

1. Root-of-trust custody and bootstrap/recovery across Android, desktop, server and edge.
2. Exact key hierarchy, algorithm registry, rotation windows and compromise response.
3. Revocation freshness and lease semantics under offline/federated operation.
4. Configuration/policy/schema precedence and atomic activation.
5. Cross-journal recovery point and external side-effect reconciliation.
6. Backup classes, RPO/RTO targets and cryptographic erasure policy.
7. Operator role separation, break-glass and emergency stop authority.
8. Telemetry/audit/evidence separation and retention.
9. Upgrade compatibility across models, agents, schemas, runtime and devices.
10. Multi-tenant isolation and data residency under provider failover.
11. Incident response and independent recovery clearance.
12. Service criticality tiers, SLOs, overload and safe degradation.

## 15. Freeze criteria

- Every lifecycle state has an owner, transition precondition and failure result.
- Every trust-zone crossing has identity, protocol, data and audit contracts.
- Key custody, rotation, revocation and recovery are complete for each deployment profile.
- Offline/partition behavior is explicit and bounded.
- Restore cannot resurrect revoked authority or corrupt audit continuity.
- Upgrade and rollback cover code, schema, policy, keys, models and data.
- External side-effect uncertainty is represented honestly.
- Operator/emergency powers are separated and accountable.
- SLO, capacity, degradation and incident lifecycle are measurable.
- Every unresolved item is explicitly deferred with owner and reason.

**Boundary:** architecture specification only. No integration, code change, test campaign, deployment or production-readiness claim follows from this document.
