# NORYX7 — Cryptographic agility and mathematical intelligence architecture

**Status:** proposed cross-cutting architecture; source reconciliation required  
**Plane mapping:** primarily P11 Security, with P07 Capabilities, P12 State, P15 Audit, P17 Performance and P18 Universal Intelligence  
**Rule:** not a new canonical plane and does not replace existing cryptographic mechanisms.

## 1. Discovery basis

The repository's architecture/source inventory identifies Ed25519 identity/signature and result attestation; AES-256-GCM authenticated encryption; HKDF-SHA256 domain-separated derivation; HMAC-SHA256 integrity/provenance seals; SHA-256 content and chain digests; key lifecycle metadata; secure channel framing, identity/session binding and replay protection; authorization replay guards and multi-principal authorization; secure boot, runtime attestation and trust-chain evidence; secure memory/storage and security integration.

Known source anchors include architecture/CRYPTOGRAPHIC_BOUNDARIES.md, core/crypto.py, core/key_lifecycle.py, core/secure_channel.py, core/authorization_replay.py, core/identity.py, core/attestation.py, core/multiauth.py, core/secure_boot.py, core/trust_chain.py, core/security_integration.py, core/secure_memory.py and core/secure_storage.py.

This is a source-family inventory, not a line-by-line audit. Exact callers, key custody providers, protocol versions, failure behavior and deployment coverage remain to be reconciled. Metadata state machines do not prove secret material is held in a KMS/HSM or hardware-backed keystore.

## 2. Cryptographic service boundaries

Separate these responsibilities conceptually, even if a later implementation shares libraries:

1. Algorithm Registry: approved identifiers, purpose constraints, parameter profiles, deprecation and compatibility.
2. Key Authority: key identity, owner, purpose, scope, lifecycle and revocation metadata.
3. Key Custody Provider: generation, storage, unwrapping, use and destruction within an explicit trust boundary.
4. Cryptographic Operations: signing, verification, encryption, decryption, key agreement, derivation, MAC and digest.
5. Trust Evidence Service: identity, attestation, secure-channel and provenance-chain validation.
6. Protocol Negotiation: compatible versions without downgrade.
7. Security Policy: allowed algorithms, key strengths, trust levels and freshness windows.
8. Audit/Evidence: algorithm/key identifiers and outcomes without secret material.

Cryptographic validity is not authorization. A valid signature proves control of a key under stated assumptions; it does not prove that signer was allowed to perform the action.

## 3. Key hierarchy and binding

Every key reference binds globally unique key ID/version; principal/device/service owner; algorithm/parameter profile; purpose (sign, encrypt, derive, attest, channel, MAC); scope, tenant and trust domain; custody provider and protection class; creation/activation/expiry/revocation; parent/wrapping key and derivation context; rotation predecessor/successor; and usage constraints where supported.

Domain separation is mandatory: keys for different purposes, tenants, protocols or environments must not be reused merely because the primitive permits it. Test keys and deterministic fixtures are isolated from production namespaces.

## 4. Rotation, revocation and compromise

Model planned rotation with overlap; emergency revocation after compromise; unavailable KMS/HSM; device replacement; offline-node freshness; old artifact verification after signer rotation; pending jobs and long-lived sessions; and ambiguous remote acknowledgement.

A retired signing key may remain necessary for historical verification while being prohibited from new signing. A compromised key may require quarantine of artifacts signed during an uncertain interval. Encryption-key destruction must account for backup/replica copies and required audit evidence.

## 5. Cryptographic agility and post-quantum migration

NORYX7 needs migration architecture independent of any one future algorithm:
- versioned algorithm identifiers and policy profiles;
- inventory of code, protocols, certificates, tokens, signatures, stored data and external dependencies;
- transition states APPROVED, PILOT, DUAL_ACCEPT, PREFERRED, DEPRECATED, DISABLED;
- hybrid/dual-signature operation only where standards, threat model and protocol permit;
- anti-downgrade binding of negotiated algorithms to authenticated transcript;
- re-encryption/re-signing strategy for long-lived data and evidence;
- interoperability, rollback, emergency disablement and compromise response.

Post-quantum readiness is evaluated by purpose and data lifetime. Key establishment, signatures and symmetric encryption have different migration needs. One quantum-resistant primitive does not solve every use case.

## 6. Mathematical Intelligence Fabric (MIF)

MIF is a capability within P18 Universal Intelligence and cross-cutting evidence/verification contracts, not an additional canonical plane. It connects mathematical discovery, formalization, independent checking and bounded application.

Logical stages:
1. Discovery of conjectures, algorithms, proof attempts and counterexamples.
2. Formalization of exact statements, definitions, assumptions and theory context.
3. Bounded proof construction or counterexample search.
4. Independent checking with checker version, dependencies, axioms and artifact digest.
5. Semantic review of formal statement versus intended claim.
6. Corollary extraction with explicit assumptions.
7. Impact analysis across cryptography, science, engineering and optimization.
8. Publication of versioned evidence-bearing capability capsules.
9. Controlled application after checking preconditions and constraints.
10. Monitoring and retirement when assumptions, dependencies or checker trust change.

## 7. Theorem and capability capsule

Each capsule contains canonical proposition/algorithm ID; exact formal statement and human interpretation; theory, definitions, axioms and assumptions; proof/certificate artifact and digest; proof assistant, checker and dependency versions; trusted computing base; independent checker results and reproducibility metadata; limitations, counterexamples and unresolved review; derived corollaries and transformation lineage; preconditions/forbidden extrapolations; publication, review and revocation status.

A capsule cannot silently upgrade a probabilistic, empirical or model-generated claim into a theorem. Formal proof establishes a proposition relative to formal assumptions; it does not prove that a physical model accurately represents reality.

## 8. Proof-carrying optimization and planning

Where practical, optimization outputs carry objective/version, constraints and source, input dataset digest, solver/algorithm/version, feasibility certificate, optimality proof or explicit gap, approximation bound, resource/time limits and termination reason.

Distinguish FEASIBLE, OPTIMAL, BOUNDED_GAP, HEURISTIC, INFEASIBLE, UNKNOWN and INDETERMINATE. A heuristic is never described as proven optimum. A proof certificate is not an execution grant: plans still require ordinary authorization, safety and ActionGate checks.

## 9. Mathematical knowledge graph

Represent dependencies among definitions, lemmas, theorems, algorithms, proof artifacts, counterexamples, datasets and applications. Type edges as depends-on, implies, refines, contradicts, formalizes, empirically-supports or applies-under. Preserve provenance and versioning. Contradictions remain visible rather than overwritten. Reuse respects exact theory and assumption context.

## 10. RH/GRH and cryptographic impact discipline

The Riemann Hypothesis and Generalized Riemann Hypothesis are useful case studies because mathematical results can affect number theory and algorithms. However:
- primality testing and integer factorization are different computational problems;
- deterministic/faster primality testing does not by itself factor RSA moduli;
- proof of RH/GRH alone is not an RSA break;
- elliptic-curve cryptography has a different mathematical basis;
- quantum risk from sufficiently capable quantum computation is separate;
- every claimed consequence must trace to a theorem with exact assumptions and a reviewed reduction or algorithm.

MIF encodes claims as conditional, source-bound capsules, not unqualified security alerts or automatic policy changes.

## 11. Security and trust constraints

- Formalization inputs and proof archives are untrusted until parsed and checked.
- Proof assistants/checkers are part of the trusted computing base and require version/provenance controls.
- Resource-bounded proof search is isolated and capped.
- Untrusted tactics/plugins cannot modify trust roots or verification policy.
- Independent verification means genuinely separate checking paths, not repeated execution of the same unchecked claim.
- Failed, incomplete or timed-out attempts remain non-proof states.
- A theorem capsule cannot grant permissions, modify keys or alter policy.
- Cryptographic policy changes require independent security review and staged release.

## 12. Open decisions before freeze

1. Map every cryptographic primitive to exact callers, protocols, stored formats and trust boundaries.
2. Identify production/test key providers and custody boundaries from source/configuration.
3. Reconcile key lifecycle metadata with actual generation, rotation, revocation and destruction.
4. Map certificate/public-key distribution and trust-anchor bootstrap for each surface.
5. Determine protocol negotiation, downgrade prevention and algorithm-version compatibility.
6. Specify post-quantum inventory and migration criteria.
7. Map attestation claims to verifier identity, measurement source and freshness.
8. Reconcile secure-channel replay windows with offline/federated delivery.
9. Define archive verification after key rotation/compromise.
10. Define MIF checker trust, capsule schema, review governance and bounded application contract.

## 13. Freeze criteria

Freeze requires complete caller/custody inventory; coherent key, certificate, identity and attestation lifecycles across deployment profiles; algorithm agility and compromise recovery; distinct formal proof and empirical evidence; versioned independently checkable MIF outputs; and ordinary policy/ActionGate authorization for every application.

**Boundary:** documentation only. No cryptographic implementation, algorithm replacement, dependency addition, proof checking, integration, testing, deployment or policy change.
