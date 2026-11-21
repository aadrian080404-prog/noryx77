# NORYX7 — Gödelian Formal Reasoning Architecture (RFC)

**Status:** architectural proposal; documentation only; not an implemented proof engine.  
**Date:** 2026-11-21  
**Scope:** integration with the existing HYPERSYNTH cognitive pipeline, metacognition, verification, ActionGate, provenance and audit.

## 1. Executive decision

Add a dedicated **Formal Reasoning and Limits (FRL)** capability to NORYX7. It is not another language model, a confidence score, or a replacement for the existing verification pipeline. It is a typed evidence path that can turn a mathematical or logical claim into a precisely specified proposition, request a proof artifact from a proof assistant, and independently check that artifact against the exact proposition and declared axioms.

Gödel's work supplies both:
- powerful formal methods: encoding syntax and proofs, diagonalisation, representability, provability predicates, and reasoning across object-level and meta-level statements;
- a discipline about limits: sufficiently expressive, consistent, effectively axiomatized theories cannot be both complete and able to prove their own consistency under the relevant hypotheses.

**Non-goal:** promise an unlimited, complete, contradiction-free reasoner. Such a promise would conflict with the mathematical results this module is intended to respect.

## 2. What the 2026 Claude results actually establish

Two projects must not be conflated.

### 2.1 Gödel's notebooks — Claude + Coq + human scholarship

Jan von Plato supplied Claude with English transcriptions of Gödel's 1940s workbooks and related books. The Guardian's 13 November 2026 report says Claude produced a large digest and surfaced 663 candidate theorems (including results Gödel had proved, sketched, or merely considered). According to von Plato, roughly 400 checked in Coq as stated, around 200 needed repaired statements or additional assumptions, and around 50 were false.

This is a report of a research workflow, not a public, independently reproducible benchmark: the full digest, candidate list and Coq files were not made available in the reporting described by the sources. Coq can check a formal proof against a formal proposition; it cannot, by itself, decide whether a transcription, historical interpretation, or formal translation faithfully captures Gödel's intended claim. Historical attribution and mathematical correctness are separate questions.

The reported reconstruction around the axiom of choice is especially important: the argument reportedly required correcting a definition. It should therefore be described as a reconstruction inspired by Gödel's notes, not automatically as an exact proof written by Gödel.

### 2.2 Gödel II in Basic Recursive Arithmetic — Claude + Agda

Thierry Coquand's June 2026 paper describes an Agda formalization of Gödel's second incompleteness theorem for Church's Basic Recursive Arithmetic (BRA), following Guard's lecture notes. The paper reports approximately 50,000 lines, produced through interaction with Claude, with no postulates; the development was checked by Agda. It is a formalization for a specified theory and proof route, not a proof that every formal system is complete or that Gödel's limits have been removed.

The experiment also records a critical failure. An initial attempt used an incorrect theorem/specification from an older source. Claude constructed a development that looked superficially like Gödel II but was mathematically unrelated, because the internal provability predicate was not specified strongly enough. The lesson is architectural: **a proof assistant can correctly check a proof of the wrong formal statement**.

The final route had to make several implicit details explicit, including proof enumeration, numeral encoding, substitution, numeral closure, and the boundary between object-level derivations and meta-level reasoning. The follow-up work formalized Chaitin's route and the Kritchman–Raz surprise-examination argument in the same Agda setting.

### Primary references

- Coquand, *Auto formalisation of Gödel's Second Incompleteness Theorem in Binary Recursive Arithmetic* (2026): https://arxiv.org/abs/2606.01898
- Coquand, *Auto formalisation of Chaitin and of the surprise incompleteness Theorem* (2026): https://arxiv.org/abs/2606.12462
- Agda development: https://github.com/coquand/agda-godel-tree
- Guardian report on Gödel's notebooks (13 Nov 2026): https://www.theguardian.com/science/2026/nov/13/kurt-godel-notebooks-ai-helps-unlock-hidden-discoveries-man-who-transformed-maths
- Independent discussion of reproducibility caveats: https://maccus.fr/en/godel-notebooks-claude/

## 3. Fit with the existing NORYX7 architecture

The current README defines HYPERSYNTH as a bounded agentic kernel with contract verification, decomposition, planning, hypothesis generation, simulation, ActionGate, execution, result admission, cross-check, output verification, metacognition, memory and audit. The existing MetacognitionEngine and PipelineChallengeVerifier check pipeline structure, identity and evidence linkage. The ChallengeDomain already includes mathematics and logic, but that challenge framework is not a formal theorem prover.

FRL must therefore be a **specialized verifier capability behind existing contracts**, not a parallel orchestrator and not a bypass around ActionGate.

### Pipeline placement

1. **Input / contract verification:** classify the claim as formal, empirical, historical, or mixed. A mathematical proof request must carry a formalization scope.
2. **Context and decomposition:** identify source texts, definitions, axioms, inference rules, theory, intended theorem, dependencies and open assumptions.
3. **Planning:** produce a bounded proof plan and select an approved backend (initially Agda for the BRA reference development; Coq for separately formalized Coq artifacts). Model choice does not determine proof validity.
4. **Hypothesis generation:** LLM agents may propose lemmas, definitions, translations, proof sketches and counterexamples. These are untrusted candidate artifacts.
5. **Formal specification gate:** check the proposition, theory, proof predicate, encoding, quantifier scope, assumptions and object/meta-level boundaries before accepting a proof attempt.
6. **Proof worker:** run the proof assistant in an isolated, resource-bounded worker. Do not execute generated proof code inside the NORYX7 gateway, identity service, or ActionGate process.
7. **Kernel verification:** the proof assistant checks the artifact against the exact formal proposition and pinned environment. A successful result is necessary but not sufficient for semantic fidelity to the source.
8. **Independent challenge:** a separate path attempts counterexamples, checks assumptions and imports, checks for holes/axioms/unsafe escapes, and compares the formal statement to the approved specification.
9. **Result admission / cross-check:** accept only a structured proof-verification result with artifact digest, exact theorem ID, theory ID, axioms, toolchain, checker output and provenance.
10. **Metacognition:** report exactly what was proved, in which theory, under which assumptions, by which checker, and what remains unverified.
11. **Memory / audit:** append immutable, content-addressed proof events. Corrections supersede prior claims; they do not silently rewrite history.

### Non-bypass rule

FRL does not grant permissions. A proof result can support an ActionGate decision, but it cannot authorize an action by itself. Existing authorization, policy, identity, provenance, risk and human-approval requirements remain in force.

## 4. Core data contracts

The following are proposed contracts, not existing Python APIs.

### FormalClaimSpec

- claim_id: stable identifier.
- informal_statement: source-language claim, preserved verbatim.
- formal_statement: exact proposition checked by the backend.
- theory_id and theory_version: exact formal system.
- axiom_manifest: explicit axioms, inference rules, definitions and imported libraries.
- encoding_manifest: syntax, Gödel numbering / code representation, substitution and provability predicate where applicable.
- scope: theorem domain and excluded cases.
- source_refs: document/page/line provenance and transcription version.
- translation_review: reviewer and review state for the informal-to-formal correspondence.

### FormalProofArtifact

- theorem and specification digests;
- source repository, immutable commit and file paths;
- proof-assistant name/version and pinned dependency manifest;
- proof source and generated artifact digests;
- checker command/configuration and complete machine-readable result;
- declared axioms, postulates, holes, unsafe pragmas and imported trust roots;
- reproducibility metadata and resource usage.

### FormalVerificationResult

Use a closed status vocabulary, never a single boolean named correct:

- CANDIDATE — model-generated idea, not checked;
- FORMALIZED — proposition encoded, semantic review incomplete;
- KERNEL_CHECKED — checker accepted the artifact for the exact formal statement;
- SPEC_REVIEWED — correspondence to the intended source statement reviewed;
- INDEPENDENTLY_REPRODUCED — separate clean build/check succeeded;
- REJECTED — counterexample, checker failure, unsound assumption, or invalid specification;
- INDETERMINATE — resource bound reached or evidence insufficient.

A theorem may be KERNEL_CHECKED but not SPEC_REVIEWED. Do not promote one state to another by model confidence, agent consensus, or repeated retries.

## 5. The object-level / meta-level boundary

This is a first-class invariant, not a documentation footnote.

- **Object level:** formulas, terms, encoded proofs, derivability, and the theory's internal provability predicate.
- **Meta level:** statements about the theory, its syntax, soundness, consistency, proof transformations and the checker.
- Every contract must label which level a statement belongs to.
- Conversions between levels require explicit, typed lemmas and a recorded justification.
- A meta-level implication must never be silently reported as a theorem derivable inside the object theory.
- A syntactic predicate that merely resembles provability is not accepted as the intended provability predicate without proving its required properties.

The Coquand experiment demonstrates why this invariant is mandatory: the initial specification was too weak, and Claude reasoned successfully inside the wrong formal target.

## 6. Gödel-aware limits registry

FRL should encode the applicability conditions of incompleteness results as structured knowledge, not use "Gödel" as a generic excuse.

For each theory T, record:
- effective axiomatizability / enumerability assumptions;
- consistency assumptions and whether they are proven, assumed, or unknown;
- arithmetic strength / representability assumptions;
- exact provability predicate and derivability conditions;
- the exact first- or second-incompleteness result formalized for T;
- whether the result is object-level or meta-level;
- which extensions or stronger metatheories are being used.

When a claim is undecidable in T, the system must say **"not decided by this theory under these assumptions"**, not "unknowable in all mathematics." A stronger theory may settle it, but that move changes the theory and its assumptions; it does not erase the original limitation. NORYX7 must never claim to prove its own global consistency merely because its tests pass.

## 7. Trust and security model

- LLM output is untrusted input, including generated Agda, Coq, Lean, build scripts and theorem statements.
- Proof workers are isolated from credentials, network access, user data and production action tools.
- No generated code runs in the main gateway or privileged runtime.
- Pin compiler/checker versions, dependencies and build images; prefer offline reproducible builds.
- Reject unresolved holes, admitted goals, postulates, unapproved axioms, unsafe escape hatches and unreviewed foreign axioms.
- Record the trusted computing base: proof kernel, compiler/runtime, imported axioms and any external checker.
- Apply CPU, memory, wall-clock, output-size and recursion limits; timeout means INDETERMINATE, never success.
- Store artifacts by digest; verify digests before replay and audit.
- A second LLM reviewer is useful for finding issues, but is not an independent mathematical proof checker.
- Proofs of empirical claims do not replace measurements, provenance, replication or real-world validation.

## 8. How Claude's workflow should be adapted — not copied blindly

The reusable pattern is:

1. Human- or source-grounded specification with precise definitions.
2. LLM decomposition into small lemmas and explicit missing assumptions.
3. Formal proof assistant as the independent kernel checker.
4. Counterexample search and adversarial review.
5. Human review of semantic fidelity and historical interpretation.
6. Reproducible artifact, versioned source and transparent reporting.

The non-reusable mistake is allowing the same model to define the target, prove it, and declare that it has proved the intended theorem. NORYX7 must separate **proposer**, **specification reviewer**, **proof producer**, **kernel checker**, and **independent auditor**. They may use the same model family for suggestions, but the final validity signal must come from the proof checker and the reviewed specification.

## 9. Implementation phases

### Phase 0 — Architecture and evidence policy
- Approve this RFC.
- Add typed statuses and provenance requirements to the architecture documentation.
- Add negative tests for wrong theorem statements, missing assumptions, object/meta-level confusion, unapproved axioms and incomplete artifacts.

### Phase 1 — Read-only Agda reference verifier
- Pin Agda and the public coquand/agda-godel-tree source at a specific commit.
- Build in an isolated offline worker using the documented safe checking mode.
- Reproduce the published BRA Gödel I / Gödel II checks without importing model-generated changes into the trusted reference.
- Store exact output and digests; no production action integration.

### Phase 2 — NORYX7 contract and audit adapter
- Introduce typed claim, artifact and result contracts.
- Bind the proof result to the task ID, execution ID, source digest and audit journal.
- Add independent specification-review and reproducibility gates.
- Keep backend calls bounded and fail closed.

### Phase 3 — Controlled autoformalization
- Allow models to propose translations and proof code only in the isolated worker.
- Require explicit reviewer approval of the formal statement before kernel-check results can be promoted.
- Add Coq as a separately pinned backend for the Gödel notebook project only when the underlying formal artifacts and source material are available and their provenance is clear.
- Add Lean only as a separately tested backend, not as an assumed universal verifier.

### Phase 4 — Broader formal reasoning
- Extend to arithmetic, logic, program invariants, cryptographic protocol properties and bounded system verification.
- Keep empirical, historical and mathematical evidence types separate.
- Publish a machine-readable proof dossier for each accepted result.

## 10. Acceptance criteria

FRL is not ready for production until all are true:

1. A known-good Agda reference theorem checks from a clean, pinned environment.
2. A deliberately wrong theorem statement is rejected or remains unapproved at the specification gate.
3. A missing or altered axiom changes the artifact manifest and invalidates the prior result.
4. A proof with a hole, postulate or unsafe escape is rejected under the selected policy.
5. A timeout, crash, unavailable backend or malformed output fails closed as INDETERMINATE / REJECTED.
6. A valid proof of the wrong proposition cannot be labeled as proof of the informal source claim.
7. Object-level and meta-level claims cannot be interchanged by serialization or adapter code.
8. A second clean worker reproduces the same theorem result and artifact digests.
9. All accepted and rejected attempts are auditable and linked to exact task and source identities.
10. Existing NORYX7 tests, security boundaries, ActionGate behavior and frozen baselines remain unchanged.

## 11. Final architectural principle

**NORYX7 must be able to reason about what it can prove, what it cannot prove within a specified theory, and why.**

Gödel's contribution is not a way to remove every limit. It is a way to make the boundary between proof, assumption, undecidability and speculation explicit. That boundary strengthens NORYX7: the system can keep exploring beyond one formal theory while never pretending that changing assumptions is the same as eliminating limitations.
