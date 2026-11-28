# NORYX7 — Structural Gate, Encrypted Persistence, Audit and Platform Assurance Reconciliation

**Review date:** 2026-11-24  
**Source snapshot:** `b009d845e6cefd87012bd1d5471e0061f8a96487`  
**Scope:** bounded read-only source inspection; architecture documentation only.

## 1. Purpose

This pass continues W01–W12 in parallel by reconciling the 18-plane structural registry with security-storage primitives, audit checkpoints, agent skills, platform adapters, Browser isolation and the planned terminal fabric. It deliberately separates:
- declared contract;
- source-level implementation;
- persistent/enforced behavior;
- independently verified assurance.

A class, registry entry, file path, cryptographic primitive or test file does not by itself establish the latter two categories.

## 2. The 18-plane gate: exact behavior and limit

### 2.1 Observed gate behavior

`core/architecture_registry.py` defines exactly the 18 enum planes and supplies a non-empty string for each of the ten `PlaneDefinition` attributes: contract, implementation boundary, integration boundary, trust boundary, failure semantics, resource budget, observability, recovery path, verification target and regression target.

`core/architecture_gate.py`:
- checks that each enum plane has a definition;
- checks that the ten fields are non-empty strings;
- tokenizes `implementation_boundary` and checks existence only for tokens ending in a recognized source suffix;
- does not parse or validate the integration boundary, trust boundary, failure semantics, budget, observability, recovery, verification or regression descriptions;
- does not trace imports, constructors, call sites, runtime reachability, enforcement points, deployment or test evidence.

Thus the gate is a useful **structural declaration/path-presence gate**. It is not an evidence-backed architecture closure gate. The word `complete` in its result is scoped to the gate's own structural predicate and must not be promoted into a claim of full system completeness.

### 2.2 Required freeze evidence

A later evidence-backed freeze manifest should bind, per plane:
1. source snapshot and required paths;
2. component owner and authoritative implementation;
3. constructors, registries, entry points and call-site graph;
4. actual integration edges and schema/version compatibility;
5. trust-boundary enforcement point and bypass analysis;
6. normal, reject, timeout, cancellation, degraded and recovery semantics;
7. resource admission, limits and overload behavior;
8. durable audit/observability owner;
9. test identifiers and evidence artifacts (without treating test existence as a pass);
10. deployment target, configuration, secrets, health and rollback;
11. unresolved assumptions, owner, severity and explicit disposition.

Freeze must be a separate state machine with signed snapshot/approvals, not a stronger interpretation of the existing boolean.

## 3. Encrypted memory and storage

### 3.1 What exists

- `core/secure_storage.py` implements an authenticated-encryption record abstraction, binding namespace and record ID as associated data and exposing ciphertext snapshots.
- `core/secure_memory.py` serializes `MemoryItem` records and delegates encryption/decryption to that store; it supports optional execution-ID filtering and deletion.
- The API is a replaceable storage boundary, but the inspected `EncryptedRecordStore` backend is a bounded in-process dictionary protected by an RLock. It is not a durable database, distributed replica or crash-surviving store.
- The serialized memory schema includes memory ID, content, kind, source, importance and execution ID; it does not include tenant/principal ownership, consent/purpose, source-artifact lineage, retention class, expiry, legal hold, deletion tombstone or replica state.

### 3.2 Assurance boundary

Authenticated encryption protects confidentiality/integrity of stored records while the key and ciphertext remain correctly managed. It does not establish:
- durable persistence or availability;
- tenant authorization or consent;
- key custody, rotation, revocation and backup recovery;
- deletion from backups, replicas, caches or derived data;
- freshness/anti-rollback;
- independent replica health or consistency.

The secure-memory adapter is a useful cryptographic storage interface, not yet proof of production memory custody.

## 4. Audit chain and checkpoint

### 4.1 What exists

`core/audit.py` maintains an in-process event list and SHA-256 hash chain. It can create an HMAC-SHA256 checkpoint over the current chain digest using an injected `KeyProvider`, and verify that checkpoint against the current in-memory chain.

### 4.2 What remains unresolved

- Events and digests are held in process memory; this class does not persist or replicate them.
- A checkpoint can authenticate a chain root if the key is protected and the checkpoint is stored independently. The class returns the checkpoint but does not itself persist it in an external immutable store.
- HMAC checkpointing proves possession of a shared secret, not independent signer identity or non-repudiation.
- The implementation does not itself provide trusted timestamping, external sequence anchoring, checkpoint cadence, retention, access control, incident ownership or restore/replay policy.

The architecture must distinguish a local hash chain, authenticated checkpoint, externally retained checkpoint, durable audit ledger and independently audited evidence.

## 5. Agent skills and platform adapter boundaries

### 5.1 Agent skills

The inspected agent-skill registry exposes named skill descriptions and local lookup/snapshot behavior. A registered skill name or agent mission does not establish qualification, current version, jurisdictional scope, independent reviewer, allowed data class or action authority. Skill metadata must be bound to a versioned manifest and delegated capability scope; skill selection cannot authorize execution.

### 5.2 Platform-neutral adapter

`core/platform.py` defines bounded typed requests/actions and routes platform actions through a `DeviceRuntimeBoundary`, checking epoch and platform identity before adapter execution. This is a useful common contract. It does not establish that every platform adapter is enrolled, attested, remotely revocable, durable or bound to a signed grant.

### 5.3 iOS adapter

The inspected Swift actor:
- holds grants and handlers in local actor memory;
- expires grants using a local clock;
- binds requests/actions to a local device ID and epoch;
- maintains a bounded in-memory consumed-action set for replay prevention;
- clears grants, handlers and consumed IDs when epoch advances.

The inspected adapter does not show signed grant issuance, durable replay state, hardware attestation, server-side revocation, remote policy refresh or crash-safe consumed-action persistence. The in-memory replay set is a local guard, not a distributed replay authority.

### 5.4 Android wake bridge

The inspected Kotlin bridge is a narrow audio wake callback boundary. It does not itself prove Android permission handling, trusted wake intent, user identity, microphone lifecycle, OS-level background execution or ActionGate authorization. Wake detection must remain distinct from user intent and authorization.

## 6. Browser isolation

`ecosystem/browser_isolation.py` scans allowed source/resource extensions in the Browser subtree for forbidden marker strings after removing comments and string literals. This helps enforce the intended AI-free Browser boundary at a static source-scan level.

It does not prove:
- absence of dynamically loaded or obfuscated integrations;
- behavior of third-party libraries and build plugins;
- runtime network destinations or WebView navigation policy;
- browser process sandboxing or Android OS permission enforcement;
- secure gateway session provisioning/revocation;
- complete coverage of generated artifacts or all build variants.

The Browser's standalone boundary remains intentional. The scanner is one structural guard, not a full mobile application security assessment.

## 7. PowerShell / Cloud Terminal status

The inspected `architecture/POWERSHELL_CLOUD_TERMINAL_FABRIC.md` defines a detailed target architecture for local sandbox, background/remote jobs, capability grants, secret injection, ephemeral compute and persistent workspace separation. The recursive source inventory in this snapshot did not show a dedicated terminal implementation subtree or runtime adapter corresponding to that specification.

Therefore the terminal fabric must be classified as **architecture specified / implementation not located in inspected tree**, not as a deployed shell capability. Any future implementation requires explicit command parsing, no shell bypass, sandbox lifecycle, remote host identity, job leases, cancellation, secrets, transcript/audit, package provenance and port-preview policy.

## 8. Cross-workstream consequences

| Workstream | New reconciliation | Remaining architecture work | Status |
|---|---|---|---|
| W01 Identity | Platform grants and local device IDs are not issuer-verified principals | Signed enrollment/grants, issuer chain, device attestation and revocation | PARTIAL |
| W02 Runtime | Structural gate does not describe lifecycle reachability; audit and replay state are local | Canonical lifecycle graph, durable audit/replay and crash recovery | PARTIAL |
| W03 Memory | Encrypted memory API exists, but inspected backend is in-memory and schema lacks tenant/consent/retention | Durable backend, ownership, purpose, expiry, tombstone and replica semantics | PARTIAL |
| W04 Agents | Skill registry is local metadata, not qualification or authority | Versioned skill manifests, independent qualification and delegated scopes | PARTIAL |
| W05 Routing | Structural registry describes budget but does not prove enforcement/capacity | Bind budgets to schedulers, admission, telemetry and overload policy | PARTIAL |
| W06 Evidence | Audit chain/checkpoint and evidence artifacts have distinct assurance semantics | Durable independent evidence custody and freeze manifest | PARTIAL |
| W07 MIRROR WORLD | Domain models still require calibration and reality-transfer evidence | Bind simulation model/version to evidence, safety envelope and Reality Bridge | PARTIAL |
| W08 Surfaces | Platform contract and local iOS/Android adapters are not complete remote trust lifecycle | Unified enrollment, permission, revocation, update and API compatibility | PARTIAL |
| W09 Security | Encryption and local replay guards are primitives, not complete key/device lifecycle | Key custody, protected checkpoints, durable replay and bypass closure | PARTIAL |
| W10 Domains | Skill labels do not qualify specialist competence | Qualification, jurisdiction, reviewer and expiry manifests | PARTIAL |
| W11 Operations | No terminal implementation located; audit/storage backends local in inspected paths | Service inventory, terminal runtime, durable telemetry, DR and release evidence | PARTIAL |
| W12 Governance | Audit/storage primitives do not implement project fund or impact accountability | Durable project ledger, consent, safeguards and independently measured outcomes | PARTIAL |

## 9. Decision reconciliation (no duplicate ADRs)

This pass does not create another ADR series. It maps findings into existing decisions:
- B77/B89: evidence-backed freeze manifest and structural-vs-evidence gate separation;
- B70: durable security events and incident lifecycle;
- B72/B78: signed supply-chain/release and independent self-improvement admission;
- B82/B102: issuer, device, session and revocation lifecycle;
- B81/B103: memory ownership, consent, deletion and context isolation;
- B99: specialist qualification;
- B104: durable offline outbox and replay/effect reconciliation.

The architecture index, source ledger and gap register should link these requirements to the exact inspected sources and keep their status OPEN.

## 10. Closure status

W01–W12 remain PARTIAL. This review adds source-level precision but does not implement persistence, attestation, terminal execution, mobile trust, runtime enforcement or freeze evidence. No test result, production readiness or architecture closure is claimed.
