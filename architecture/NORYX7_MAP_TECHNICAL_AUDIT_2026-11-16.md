# NORYX7 — Technical audit of the proposed architecture map
Date: 2026-11-16

## Purpose and evidence rules

This review separates (1) source code present on `main`, (2) draft PR implementations, (3) external research or third-party projects, and (4) hypotheses or metaphors. A name, paper, patent, benchmark, passing unit test, or architecture document is not by itself evidence of a production-ready NORYX7 capability.

No claim in this document means that a component has been merged or deployed. Draft PRs remain isolated. The frozen architecture branch and `main` are not modified by this review.

## Executive finding

The map contains useful design directions, but it mixes mature security principles, research prototypes, speculative physical channels, metaphors, and factual claims with very different evidence levels. Integrating every item literally would weaken NORYX7. The correct approach is to adopt the defensible properties, replace unsafe formulations, and defer unproven mechanisms.

The highest-value work is not FractalShield, neutrino links, Schumann broadcasts, or a large collection of named agents. It is closing the actual end-to-end trust path:

verified identity and consent -> attenuated capability -> taint-aware policy gate -> bounded target execution -> independent result verification -> append-only audit -> scoped memory/offline sync -> revocation and recovery.

## 1. What exists in NORYX7 today

### Main branch baseline

The audited main baseline is `7d900bc75843ea968aa5886d251dbfac83a5d93b` (as recorded by the repository audit). It contains real foundations:

- cognitive/runtime foundations in `core/hypersynth.py`, `core/hypersynth_runtime.py`, and operational runtime;
- local Agent Fabric and Model Fabric, including an OpenRouter adapter;
- gateway and bootstrap authentication;
- local audit and identity/security primitives;
- L0-L5 memory primitives and offline execution/synchronization abstractions;
- Android WebView browser project.

These are working foundations, not a completed distributed sovereign operating system. In particular, main's device fabric is an in-memory registry, the original offline queue is process-local, and the key lifecycle is metadata plus an external key boundary. The gateway bootstrap bearer proves possession of a shared secret; it does not independently prove a human or device identity.

### Draft PRs / isolated branches

| Area | Existing candidate | Evidence and remaining boundary |
|---|---|---|
| Runtime startup and gateway assurance | PR #85 | Startup cleanup, idempotent shutdown and explicit `bootstrap_bearer_only` assurance. All listed checks passed on the then-current PR head. It does not authenticate a person/device. |
| Durable offline outbox | PR #86 | SQLite outbox with encrypted payload records, idempotency and tamper checks. Five checks passed on its exact head. It is not a durable snapshot store, rollback-resistant anchor or exactly-once remote execution. |
| Durable key lifecycle metadata | PR #87 | SQLite key metadata, transactional lifecycle transitions and concurrency tests. Checks passed on its exact head. It stores no key material and is not an HSM/KMS. |
| Matrix durable stop intents | PR #83, based on PR #73 | Durable local stop intents and admission fencing. Depends on Matrix core integration; not distributed consensus or OS process termination proof. |
| Target-side generation fence | PR #88 | Target-node SQLite fence and local executor adapter. Its initial CI failed during test collection because the implementation class was missing from the module. Follow-up commits completed the class, persisted a pre-launch `starting` intent, rechecked the grant/task state under the SQLite write lock, added a legacy-schema migration and recovery tests. Current reviewed head: `f623fcefbc54f0ccc995b66d73fcea2670c97acb`; at the time of this update, test and Foundation workflows were still running, while Runner Smoke and Source Secrecy had passed. Do not call the current head green until all exact-SHA checks finish. |
| Principal-scoped memory | PR #84 | Process-local namespace isolation and quotas. It still needs a verified caller identity, durable encrypted persistence and cross-device consistency. |
| Distributed memory validation | PR #70 | Input validation and causal metadata hardening; not a complete distributed consistency protocol. |
| Identity registry | PR #46 | Durable identity metadata candidate. A stable protected signing-key provider remains a separate requirement. |
| Quorum witness / SURF inspector | PR #66 / #72 | Candidate branches; not yet part of the canonical runtime or a complete evidence-to-action pipeline. |

The architecture integration manifest is a useful dependency inventory, but its validation proves graph consistency and path existence, not operational readiness.

## 2. Review of the ten architectural principles

| Proposed principle | Decision | Safe operational interpretation |
|---|---|---|
| Double decentralization | Keep as target | Separate node/resource decentralization from governance decentralization. Add explicit quorum, failure-domain, Sybil-resistance and recovery rules. Current device registry is not yet a global P2P fabric. |
| Coherentism | Correct | Internal consistency is necessary but not truth. Every factual claim needs provenance, evidence, timestamps, uncertainty and contradiction handling. A coherent false story remains false. |
| Living computation | Reject literal unbounded growth | Never let attack traffic cause unbounded resource absorption. Use fixed budgets, rate limits, backpressure, quotas, circuit breakers and bounded decoys. |
| Fractality | Keep as design heuristic | Reuse the same security invariants at device, edge, cluster and service scale. Self-similarity is not a security proof. |
| Asymmetry of limits | Keep and formalize | The root policy, identity anchors and safety invariants cannot be rewritten by an agent. Changes require signed policy updates, independent review, tests and rollback. |
| Temporal indistinguishability | Redesign | Model observable leakage explicitly (timing, size, access patterns, errors, cache, network). Key rotation alone does not make states indistinguishable. |
| Isolation from outside | Correct | Treat external content as untrusted and tainted. Browsing itself does not mean compromise; browsing must be sandboxed, mediated and unable to invoke privileged sinks without authorization. |
| State != Government | Keep as governance objective | Separate durable institutional rules from temporary operators. Governance, appeal, audit and jurisdiction remain to be implemented. |
| Skill, not memories | Correct | Minimize retained personal data and convert repeated work into reusable skills only with consent and validation. Do not erase evidence needed for security, user recovery or legal obligations. |
| Chaos inside, calm outside | Keep as UX/research metaphor | Internal exploration may branch, but externally visible actions must be bounded, reproducible where possible, evidence-backed and auditable. |

## 3. Agent security and verification components

### ActShield

An external public repository exists under the ActShield name and describes a deterministic AI security control plane, capability checking, delegation attenuation and taint barriers. It is not a NORYX7 component and its README is not proof of an independently audited, production-grade six-layer implementation.

**Adopt the properties, not an unreviewed dependency:** create a NORYX7 reference monitor with explicit action schemas, capability tokens bound to actor/task/resource/expiry, monotonic privilege attenuation, taint labels, deny-by-default sink checks, revocation and audit. Test prompt injection, confused deputy, replay, delegation escalation and cross-tenant access.

### CRSA-1

The map does not provide a verifiable paper, standard, source repository or formal specification for the exact CRSA-1 framework described. Treat it as a proposed NORYX7 design, not an established standard.

**Build a scoped attestation envelope:** component identity, version, configuration digest, inputs/outputs, policy version, test evidence, assumptions, expiry, signer and revocation status. Composition must preserve assumptions and reject incompatible certificates. A hash-chain audit record is tamper-evident, not automatically immutable or truthful.

### SAVeR

A real 2026 ACL paper titled *Verify Before You Commit: Towards Faithful Reasoning in LLM Agents via Self-Auditing* describes SAVeR. Its experiments support the research direction, not a guarantee that every agent belief is correct.

**Integrate as an optional reasoning audit stage:** claims are decomposed, evidence-bound, challenged, repaired and checked against explicit acceptance criteria. A separate deterministic verifier must handle machine-checkable constraints. If evidence is missing, the system must preserve uncertainty rather than manufacture certainty.

### MACV

A 2026 IEEE conference publication describes Multi-Agent Cross-Verification. Cross-checking is useful but agent agreement is not independent evidence; agents can share the same model, data, prompt injection or blind spot.

**Use heterogeneous checks with provenance diversity:** source retrieval, domain validators, deterministic tests, adversarial review and independent models. Consensus is a routing signal, not proof. Track correlated failure modes and allow a valid dissenting witness.

### CT Toolkit / Nested Agency / Divergence Engine

The exact toolkit and three-level implementation in the map are not established in the NORYX7 repository by the evidence reviewed. Constitutional policies and divergence monitoring are valid design requirements.

**Implement the minimal NORYX7 form first:** immutable policy version, agent/task lineage, action and belief deltas, drift metrics, quarantine, review and rollback. LLM-as-judge must never be the sole authority to revoke identities or rotate production keys.

## 4. Drift monitoring and coherence

### Moral Anchor System (MAS)

A 2025 arXiv preprint and 2026 conference record describe a proposed Bayesian/LSTM framework. The stated 80% reduction and 85% accuracy are reported research/simulation claims, not a production guarantee or a universal benchmark.

Adopt the monitoring idea only after defining measurable policy violations, ground-truth labels, false-positive/negative costs, drift windows and domain-specific baselines. A drift event should trigger a reversible, least-privilege response (pause sensitive actions, quarantine, inspect), not an automatic permanent shutdown.

### PSI + chi-square + KS

These are established statistical tools, but the map's fixed `PSI > 0.25` threshold and “within 80 transactions” statement are not universal safety thresholds. They depend on sample size, feature distribution, expected counts, seasonality and multiple-testing effects.

Implement them as telemetry signals with calibrated baselines, minimum sample sizes, confidence intervals, alert hysteresis and human review. Test prompt-induced behavioral changes, benign distribution shifts and adversarial evasion. Do not make one statistical score a security authorization.

### Prime-Radiant / sheaf Laplacian

An external crate/repository uses sheaf-Laplacian language for structural consistency. This is a possible mathematical diagnostic, not a universal truth detector. An energy of zero only means consistency under the chosen graph, representations and restriction maps.

Prototype it offline on contradiction datasets. Compare against simpler graph and rule-based baselines. Use it to surface inconsistency and select further checks, never as the only gate for factual truth or high-impact actions.

## 5. Cryptography, deception and privacy

| Proposal | Decision | Reason / safe alternative |
|---|---|---|
| FractalShield | Research-only; do not use for production keys | The material found is a technical note and a third-party project, not a widely audited cryptographic standard. Claimed geometric cost factors do not establish security. Use established password KDFs and authenticated encryption; independently review any experimental construction. |
| Multiverse Path Encryption | Do not use as encryption/authentication | Producing plausible alternative plaintexts is not a substitute for authenticity. NORYX7 must reject wrong keys/tampered ciphertexts, not accept coherent false interpretations. |
| Oblivious Computing / “4+4=20” | Reject as a user-facing correctness rule | Deliberately false outputs violate integrity. Privacy mechanisms belong in the data path (constant-time operations, padding, batching, ORAM where justified, differential privacy with explicit budgets), never in the truthfulness of user answers. |
| Proactive key refresh / PSS | Keep as a future cryptographic workstream | Proactive secret sharing is a real research area, but requires a defined threshold protocol, secure share refresh, authenticated participants, epoch management, rollback protection and audited implementation. Do not improvise a home-grown MPC protocol. |
| BBKR linked to drift | Defer automatic coupling | Drift may trigger a security incident workflow, but key revocation/rotation must depend on cryptographic compromise evidence and policy. A noisy LLM judge must not trigger irreversible key destruction. |
| Honey encryption | Restricted research/deception use | It is domain-dependent; published analysis notes that wrong-key plaintexts can be recognized if the message space is poorly designed. It is not a replacement for AEAD. |
| FIEGE / generated fake documents | Isolated honeypot only | Deception must be separated from real user data, production workflows and external decision-making. Never poison NORYX7's trusted memory or mislead legitimate users. |
| Synthetic plates/noise | Test data only | Synthetic generation can reduce direct exposure, but collision, memorization and re-identification still need testing. Use generated data in tests, not as a security primitive. |

Production cryptography should use maintained, reviewed libraries and standard constructions, with explicit key separation, authenticated encryption, signature verification, nonce discipline, secure key custody and rotation. The current SQLite key lifecycle candidate tracks metadata only; it does not provide key custody.

## 6. Physical channels

### Neutrino key exchange

EP4770003A1 is a published European patent application assigned to Deutsche Telekom, with a 2024 priority date and publication on 1 July 2026. A patent publication is evidence that an application was published, not evidence of a deployed, independently validated or economically practical communications system. The described trusted node is itself part of the trust boundary and handles key material.

**Decision:** no NORYX7 dependency, no architecture assumption and no security claim based on neutrinos. Revisit only if there is a demonstrated end-to-end system, public measurements, threat analysis and independent validation.

### Schumann resonance / 35 bit/s

The map's claim of a 35 bit/s Schumann-resonance communications channel was not substantiated by reliable technical evidence in this review. The existence of natural ELF resonances does not establish a practical, controllable, authenticated broadcast channel with that throughput.

**Decision:** do not design heartbeat, emergency broadcast or vault recovery around it. Use tested terrestrial radio/satellite/mesh paths with authenticated, low-bandwidth emergency protocols and documented coverage.

## 7. Real-world cases in the map

- **Bari, 15 November 2026:** the reported investigation into two young suspects and alleged theft of digital identities, credentials and card PINs is supported by ANSA and Rai News. It is an investigation/allegation, not a final conviction. Use it to test credential theft, account recovery, device binding, phishing-resistant authentication and least privilege.
- **Fireworks AI, 16 July 2026:** Fireworks' own release reports a $1.505B Series D at a $17.5B valuation. This is a company-reported financing announcement, not proof of the strategic claim that central inference is inherently unsafe or that NORYX7 is its direct technical counterpart.
- **Binance, $6.3B, October 2026:** a Financial Times report describes a reported theft and a compromised DevOps engineer laptop. The map's specific EIP-7702 persistent-delegation detail was not independently substantiated in the sources reviewed. Treat the case as a threat-model scenario pending primary incident details.
- **“Pietro Miotti / 48 AI agents”:** no reliable source was identified for the exact event as stated. Keep it out of the evidence-backed threat model until a verifiable source is supplied.

## 8. Missing components that should be built

Priority order:

1. **Identity and trust binding:** device keys, user authentication, secure enrollment, attestation policy, revocation, session binding and explicit assurance levels. Bootstrap bearer possession must never be mislabeled as verified identity.
2. **Capability and taint reference monitor:** every tool/API/process action passes one deterministic policy boundary; delegated capabilities can only narrow; untrusted input cannot become executable instruction without explicit validation.
3. **Target process supervisor:** stable process identity, launch/stop reconciliation after crashes, idempotent stop, generation fencing, resource limits, sandbox profile and verified cleanup.
4. **Unified audit/evidence ledger:** append-only sequence, hash chaining, signed checkpoints, provenance, policy and model versions, privacy redaction, retention and independent verification. Hash chains detect tampering only relative to a trusted checkpoint.
5. **Offline state recovery:** durable authenticated snapshots, protected monotonic/anti-rollback anchor, key custody, conflict resolution and replay-safe sync. The outbox alone is not a complete offline runtime.
6. **Distributed device fabric:** authenticated peer discovery, opt-in grants, capability negotiation, resource accounting, failure domains, revocation propagation, partition handling and bounded consensus.
7. **Memory isolation:** verified principal binding, per-principal encryption, retention/deletion policy, provenance, causal consistency, anti-replay and restore tests.
8. **Independent verification pipeline:** evidence-bound claims, deterministic policy/model checks, adversarial test generation, result verification and explicit abstention.
9. **SURF reverse engineering pipeline:** authorized targets only, passive capture first, sandboxed dynamic analysis, reproducible evidence, differential tests, vulnerability triage and safe disclosure. No untrusted binary execution on the host.
10. **Drift/health monitoring:** calibrated statistical baselines, bounded anomaly response, operator review and rollback.
11. **Android/device integration:** secure device enrollment, local key protection, permission boundaries, battery/thermal/resource limits, offline sync and lifecycle tests.
12. **Governance and community systems:** transparent rules, appeal, independent witnesses, consent and financial accountability. These remain product/governance work, not existing runtime capabilities.

## 9. End-to-end acceptance gates

A component is not “working” merely because its unit tests pass. The following end-to-end scenarios must pass before calling the system operational:

- bootstrap bearer cannot create a verified principal;
- a verified device can obtain only explicitly consented capabilities;
- delegated agents cannot expand capabilities or remove taint labels;
- a prompt-injected document cannot trigger a privileged action;
- revoked generations cannot start new work on any target node;
- crash between process launch and database commit is reconciled without duplicate execution;
- stop failure remains durable and retries safely;
- offline queue survives restart, detects tampering and rejects rollback;
- encrypted memory cannot be read across principals;
- an agent result cannot be committed without independent verification and audit evidence;
- audit tampering is detected against a separately protected checkpoint;
- a network partition does not silently widen permissions or duplicate irreversible side effects;
- Android/browser permissions and local secrets remain bounded and revocable.

Each test must state the threat, preconditions, expected denial/allowance, evidence emitted and recovery behavior. CI must be green on the exact commit SHA being evaluated.

## 10. Recommended implementation sequence

**Phase A — Stabilize current candidate PRs:** repair and rerun PR #88; recheck exact heads of PR #85–#87; reconcile branch bases and dependencies before any integration. Do not merge while dependencies are stale or the full suite is red.

**Phase B — Close the trust chain:** identity assurance -> capabilities -> taint gate -> target supervisor -> audit ledger. This is the first production-critical vertical slice.

**Phase C — Persistence and distributed safety:** durable offline snapshots and anti-rollback, key provider adapter, principal-bound memory, peer authentication, partition/replay behavior.

**Phase D — Cognitive assurance:** SAVeR-style evidence audit, deterministic verifiers, heterogeneous cross-checking, coherence diagnostics and calibrated drift signals.

**Phase E — SURF and device integration:** safe reverse engineering, Android enrollment, reproducible testing, local/edge resource orchestration.

**Phase F — Advanced research:** sheaf diagnostics, threshold key refresh, honey encryption in isolated decoys and privacy-preserving traffic shaping. Physical channels and experimental cryptography remain excluded unless independently demonstrated.

## Sources checked

- ActShield public repository: https://github.com/Tarunvoff/ACT-SHIELD
- SAVeR, ACL Anthology: https://aclanthology.org/2026.acl-long.1440/
- MACV, IEEE Xplore: https://ieeexplore.ieee.org/abstract/document/11412804
- MAS preprint: https://arxiv.org/abs/2510.04073
- Prime-Radiant crate overview: https://docs.rs/crate/prime-radiant/latest
- EP4770003A1 patent publication: https://patents.google.com/patent/EP4770003A1/en
- Honey encryption limitations paper: https://onlinelibrary.wiley.com/doi/10.1155/2017/6760532
- Bari report, ANSA 15 Nov 2026: https://www.ansa.it/sito/notizie/cronaca/2026/11/15/hacker-15enni-rubavano-identita-digitale-e-dati-sensibili-_63f9d5bd-69f5-4d9b-a5a4-1e157c63f6ec.html
- Fireworks financing release, 16 Jul 2026: https://fireworks.ai/news/fireworks-raises-1-5-billion-series-d
- Binance incident reporting, Financial Times: https://www.ft.com/content/58fee10f-8a99-4e8b-835d-ddba5e434ce3

## Final decision

NORYX7 should adopt the security properties that can be specified, tested and independently verified. It should not adopt unverified performance numbers, speculative physical channels, nonstandard cryptography or intentional false answers as security mechanisms. The target is a coherent, evidence-backed and recoverable system whose safety boundaries remain enforceable even when an agent, model, device, network peer or operator is compromised.
