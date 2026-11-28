# NORYX7 — Four-front identity, global memory and ecosystem governance reconciliation

**Review date:** 2026-11-23  
**Source baseline:** `main`, architecture-only review  
**Scope:** W01/W02/W03/W08/W09/W12; no implementation or verification campaign.

## 1. Four-front model: boundary contract versus operational product

The repository defines four fronts in `ecosystem/boundaries.py`: JARVIS, Browser, HYPERSYNTH and Orchestration. The `IntentEnvelope` binds intent ID, front, operation, payload digest and principal label. Payload is represented by a digest, not carried as a typed canonical action contract.

The helper `make_intent` derives a deterministic intent ID from front, operation, principal label and payload digest. When no principal is supplied, it defaults the principal label to `front.value`. This is a convenience default, not an authenticated principal. It must never be accepted as a real user, workload or device identity by a privileged boundary.

`ecosystem/runtime_dispatch.py` checks source/front consistency, a non-empty principal label, an injected authorization callback, topology isolation and an execution ID before invoking a handler. It returns a dispatch receipt with accepted/rejected outcome and a digest of exception/value type metadata. This is a useful cross-front guard, but the callback's trust root and decision evidence are external; a receipt is not automatically a signed durable execution record. The handler's successful return is accepted at the dispatch layer without domain-specific result verification or state commit semantics in this function.

`ecosystem/front_runtime.py` provides thin JARVIS and HYPERSYNTH adapters. These adapters do not establish a single system-wide request lifecycle owner or resolve the previously identified separate JARVIS and RuntimeEngine state stores.

The `closure_contract.py` and `structural_manifest.py` enumerate required boundary names, security invariants and file paths for four fronts. They validate structural shape and path presence. They do not prove that every declared boundary is invoked on every path, that a privileged path cannot bypass dispatch, or that the referenced source is complete.

### Canonical requirement

Each front is a presentation/interaction and bounded adapter surface, not an independent authority domain. Every front must resolve the same principal/tenant/session/device/execution identity graph and submit typed requests to one canonical lifecycle. The front may not mint trusted principal identity from its own name, UI session label or caller-supplied metadata.

## 2. Intent and dispatch receipt semantics

The current intent ID is deterministic for identical front/operation/principal/payload digest. That can aid deduplication but does not replace a separately scoped idempotency key: two intentionally distinct operations with identical content could collide at the semantic level if consumers treat intent ID as globally unique transaction identity. Conversely, an attacker who can choose all fields can reproduce the same identifier. Identity, uniqueness, replay protection and idempotency must be separate fields with separate issuers and retention.

The canonical dispatch contract must bind:
- request/intent ID and separately issued idempotency key;
- principal, issuer, tenant, session and device assurance;
- source and target front;
- typed operation schema/version and canonical payload digest;
- action digest, policy version/epoch and authorization evidence;
- execution ID, trace/correlation IDs and deadline;
- resource budget, data residency and consent purpose;
- dispatch lease/fencing token and retry semantics;
- result digest, verification evidence, state commit receipt and final lifecycle outcome.

Dispatch receipt outcomes must distinguish not accepted, accepted but not started, running, completed, rejected, failed before effect, failed after possible effect, indeterminate, partially completed and compensated. A boolean accepted flag cannot represent the entire lifecycle.

## 3. Global memory and identity authorization index

`ecosystem/global_fabric.py` defines L0–L5 memory levels and a `MemoryRecord` with record ID, level, version, payload digest, replica labels and provenance digest. `GlobalMemoryFabric` stores these records in an in-memory dictionary. It receives payload/provenance bytes but retains only their digests in the record; durable encrypted content storage, retrieval authorization, tenant partitioning, replica health, key custody, consistency, retention, deletion and recovery are external.

The method `require_redundancy` counts replica labels; it does not check that replicas are independent, online, in distinct failure domains or contain the verified same ciphertext/version. A replica count is not durability evidence.

`IdentityAuthorization` records identity/session/device IDs, role, capabilities and policy/authorization digests. `GlobalIdentityAuthorizationFabric` is an in-memory session index. Binding prevents a session from being rebound to a different identity/device in the local process, while authorization compares a supplied policy digest and capability. This is a local lookup primitive, not an issuer signature, expiry check, tenant check, revocation registry or cross-region consensus service.

### Memory authority rules

- Memory stores content/evidence, never authorization authority.
- Retrieval must enforce tenant and principal scope before content enters a prompt.
- Every record binds source lineage, data class, consent purpose, expiry, retention, deletion/tombstone and schema version.
- L0–L5 represent storage/latency tiers, not different permission levels.
- Promotion/demotion must preserve lineage, encryption, access policy and deletion propagation.
- Replication requires verified replica identity, independent failure domains, digest agreement and recovery protocol.
- A tombstone must prevent stale replicas/backups from resurrecting deleted data.
- Cross-tier memory must define consistency, stale-read policy, conflict resolution and offline reconciliation.

### Identity authority rules

The session index is a cache/index of already-authorized state, not the authority that creates it. Canonical authorization evidence must bind issuer, principal type, tenant, device/session, capabilities, audience, expiry, policy epoch, key ID and revocation state. A cached allow must fail closed or enter a documented reduced-assurance mode when freshness cannot be established.

## 4. Ecosystem/product fabric: architecture intent versus source implementation

The inspected `ecosystem/` source inventory contains front boundaries, browser isolation, dispatch contracts, front runtime adapters, global closure/completeness, global fabric, global scale and structural manifests. It does not contain dedicated implementation modules named marketplace, finance, governance, community, business, billing or ledger in that package. This is a bounded inventory observation, not proof that no related functionality exists elsewhere in the repository.

The existing `architecture/BUSINESS_PROJECT_FABRIC.md` is a product/workflow architecture document. It specifies opportunity through accounting/audit lifecycle, supplier/service workflows, transparent commissions, separation of customer/third-party/company funds and explicit authorization before financial execution. Those are architectural requirements, not evidence that payment rails, ledger posting, reconciliation or dispute/refund execution are implemented in the inspected ecosystem package.

Likewise, the existing `architecture/USER_UNDERSTANDING_FABRIC.md` establishes valuable non-surveillance and non-authority constraints: explicit consent, data minimization, sensitive-trait exclusions and prohibition on using personalization as security authority. The newer source review still requires durable consent receipts, correction/deletion propagation and evidence lineage before that lifecycle can be considered operationally closed.

### Product and financial boundaries

NORYX7 must keep these ledgers and roles separate:
1. user-owned funds and user-authorized transactions;
2. third-party/merchant/customer funds;
3. company operating revenue;
4. community/project pooled contributions;
5. grants/donations and restricted-purpose funds;
6. commissions, fees, refunds, chargebacks and taxes.

A single account balance must not blur beneficial ownership or restricted-purpose obligations. No model, agent, marketplace listing or community vote may directly move funds. Money movement requires a regulated/authorized provider, explicit consent, beneficiary and purpose verification, transaction limits, sanctions/fraud/compliance checks where applicable, idempotency, double-entry ledger, settlement receipt and dispute path.

### Marketplace trust

A marketplace requires verified seller identity, product/service provenance, transparent fees, availability/fulfilment contract, escrow/settlement provider boundary where applicable, refund/dispute process, fraud reporting and buyer protection. Listings, reviews and rankings must be separated from paid placement and bot-generated manipulation. Recommendations cannot silently become endorsements or guarantees.

### Community governance

Community contribution systems require explicit membership, project purpose, transparent budgets, decision rights, conflict-of-interest declarations, quorum/appeal, safeguarding, worker safety, compensation rules, exit/refund policy, independent audit and anti-capture controls. Participation and governance must not be reduced to financial contribution; non-financial labor, expertise and local impact need fair, auditable recognition. No automated agent should hold unreviewable authority over community funds or membership rights.

### Environmental and social impact

Impact claims must be measured against explicit baselines, boundaries, time periods and independent evidence. Distinguish gross activity (waste collected, trees planted, money donated) from net outcome (material recovered, emissions avoided, ecosystem restoration, long-term survival, displacement/leakage and rebound effects). Use independent measurement and uncertainty ranges; do not monetize or aggregate incompatible impacts into a misleading single score.

## 5. Cross-front and ecosystem decisions added

| ADR | Streams | Decision required |
|---|---|---|
| B79 | W01/W02/W08 | Front identity must resolve to canonical principal; prohibit front-name fallback as authenticated identity |
| B80 | W01/W02/W03/W08 | Separate intent, request, idempotency, execution and dispatch receipt IDs; define full dispatch lifecycle outcomes |
| B81 | W03/W06/W09/W12 | Global memory replication, tenant isolation, provenance, retention, tombstones and cross-tier consistency |
| B82 | W01/W09/W12 | Canonical identity authorization issuer, expiry, tenant, policy epoch, revocation and cache freshness |
| B83 | W09/W12 | Marketplace/financial ledger, funds segregation, regulated payment provider and transaction authorization boundaries |
| B84 | W10/W12 | Community governance, worker safeguarding, transparent pooled funds and independently measured social/environmental impact |

## 6. Workstream disposition

- **W01:** front-derived principal fallback and local identity index are mapped; canonical issuer graph and session authorization freshness remain open.
- **W02:** cross-front dispatch wrapper and front adapters are mapped; single lifecycle owner and state transaction semantics remain open.
- **W03:** global memory is an in-memory index with replica labels; durable encrypted storage, consistency and tombstones remain open.
- **W08:** four front boundaries and dispatch contracts mapped; complete ingress, lifecycle and capability parity remain open.
- **W09:** identity index is not an authority root; signed authorization, revocation and cache freshness remain open.
- **W12:** business/project fabric is architecture intent; payment, ledger, marketplace, community and impact operations require separate governed contracts and source reconciliation.
- **W04/W05/W06/W07/W10/W11:** no closure status upgrade implied; their agent, routing, evidence, simulation, domain and operations work continues under existing registers.

## 7. Freeze conditions

Before integration, freeze package must define canonical front identity, dispatch lifecycle, memory consistency/deletion, authorization freshness, ledger/funds segregation and community/impact governance. Any missing implementation module must be classified as absent, planned, external provider dependency or unknown; architecture documentation must not describe a planned product feature as an implemented capability.
