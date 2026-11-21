# NEXUS — NORYX7 architecture audit and integration specification

**Status:** draft architecture/audit artifact; not an implementation claim  
**Date:** 2026-11-21  
**Scope:** source repository `aadrian080404-prog/noryx77`; transfer/verification repository `aadrian080404-prog/noryx7-verified`  
**Compatibility rule:** additive integration only; existing contracts, identity, authorization, runtime and frozen baselines are not replaced.

## 1. Executive finding

The source repository already contains several prerequisites for a native semantic exchange layer: typed task/action/result contracts, immutable-ish context snapshots, bounded memory, agent identity and skill registration, operational dispatch, evidence-bearing domain assessments, planning, metacognitive pipeline checks, runtime envelopes and signed attestations.

The inspected implementation does **not** establish that a complete native semantic language already exists. Several central meaning-bearing fields remain plain strings, while context, memory and action parameter payloads admit generic values. There is no verified, end-to-end semantic type system, canonical concept/relation graph, semantic wire protocol, vocabulary governance/version negotiation, general multimodal semantic representation, or semantic-preservation verifier identified in the inspected paths.

The correct next step is therefore **not** to create a second orchestrator, agent fabric, memory, identity system, authorization layer or proof engine. It is to define NEXUS as a typed semantic representation and exchange boundary, then connect it through adapters to existing HYPERSYNTH components.

This is an architecture audit based on the files and refs listed below, not a claim that every file on every branch has been exhaustively inspected. GitHub code search returned no usable indexed matches during this pass; file-level inspection was performed through known repository paths. Missing paths/search results are recorded as unknown, not proof of absence.

## 2. Repository boundaries and evidence

### 2.1 `noryx77` — source/integration target

The default-branch files inspected include:

- `README.md`
- `requirements.txt`
- `core/__init__.py`
- `core/contracts.py`
- `core/agent_core.py`
- `core/agent_fabric.py`
- `core/operational_fabric.py`
- `core/universal_intelligence.py`
- `core/context.py`
- `core/memory.py`
- `core/planning.py`
- `core/reasoning.py`
- `core/metacognition.py`
- `noryx7_runtime/contracts.py`
- `noryx7_runtime/engine.py`

The README describes HYPERSYNTH as a bounded cognitive kernel and gives the pipeline: perception/contract verification → context → decomposition → planning/plan verification → hypothesis/verification → simulation → resource allocation → ActionGate/security → agent execution → result admission → cross-check/consensus → output verification → metacognition → memory/audit.

### 2.2 `noryx7-verified` — limited transfer/verification repository

Its README states that only the first cryptography block was inserted (2026-11-13), that other blocks in the initial map have not yet been imported, and that automatic tests have not yet been run in this repository. Its `AUDIT_PRELIMINARY.md` explicitly marks the block as not runtime-validated and lists stubs and compatibility/resource concerns.

Consequently, this repository cannot currently be treated as a complete mirror or independent verified implementation of the NORYX7 cognitive architecture. NEXUS must not be implemented there as if the HYPERSYNTH interfaces were present. The crypto repository may later provide cryptographic primitives for signed NEXUS artifacts, subject to its own validation gates; it must not define semantic truth or grant execution authority.

## 3. Existing-component inventory and exact integration roles

| Existing path / type | Observed representation | NEXUS relationship | Required change |
|---|---|---|---|
| `core/contracts.py:TaskSpec` | `task_type`, `objective`, `input`, `constraints`, verification requirements | Task/goal semantic binding | Add optional adapter; do not replace current contract |
| `core/contracts.py:ActionSpec` | action type, target, generic parameter mapping, risk and authorization flag | Semantic action proposal | NEXUS action meaning remains non-authoritative; ActionGate remains decisive |
| `core/contracts.py:AgentResult` | output plus verification and execution identity | Semantic result/evidence binding | Preserve result admission and execution provenance |
| `core/agent_core.py:AgentInput` | `content: str`, mode, generic context | Natural-language ingress adapter | Parse into NEXUS only as a candidate; retain original input/source |
| `core/agent_core.py:AgentContext` | objective string, input, facts mapping | Context projection | Add typed semantic references, not another context store |
| `core/agent_core.py:AgentPlan` | tuple of step strings | Human-readable plan projection | Prefer existing canonical `core/planning.py:Plan` path for operational plan |
| `core/agent_core.py:AgentResponse` | content string, mode, verified boolean | Egress projection | Render NEXUS results; do not equate boolean with formal proof |
| `core/agent_fabric.py:AgentFabric` | trusted identity, skills, principal authorization, bounded dispatch | Transport/recipient and capability resolution | Add message adapter; never bypass principal authorization |
| `core/operational_fabric.py:OperationalAgentFabric` | select, dispatch, admit | Execution boundary | NEXUS cannot dispatch directly; use existing fabric |
| `core/universal_intelligence.py:Evidence` | evidence id, source, claim string, strength | Evidence node and provenance link | Replace free-form meaning only through compatible typed wrapper |
| `DomainAssessment` | domain, conclusion string, evidence, confidence, uncertainty, contradictions | Epistemic assessment | Add typed claim references and explicit status |
| `SpecialistRoute` / `FabricResult` | domain route and commit eligibility | Semantic routing/result metadata | Routing remains policy-bounded; semantic labels grant no capability |
| `core/context.py:ContextSnapshot` | task id, `dict[str, Any]`, source ids, version | Semantic context projection | Add immutable validated NEXUS references; avoid storing unvalidated graphs |
| `core/memory.py:MemoryItem` | generic content, kind, source, importance, execution id | Semantic memory record | Store canonical references/digests; preserve existing memory isolation and limits |
| `core/planning.py:PlanStep` | objective string, action type, risk, dependencies | Goal/step semantic binding | Maintain step identity/dependency validation |
| `core/reasoning.py:Hypothesis` | statement string, basis ids | Hypothesis claim + supporting graph | Add typed proposition reference and epistemic status |
| `core/metacognition.py:MetacognitionEngine` | pipeline count/identity/basis checks | Independent semantic integrity challenge | Extend with semantic invariants; never treat it as a theorem prover |
| `noryx7_runtime/contracts.py:Intent` | text string, principal id, intent id | Ingress intent binding | Add optional NEXUS ref alongside legacy text |
| `ActionEnvelope` | execution/principal/step/action/target/parameters/nonce | Runtime action projection | Semantic payload cannot alter identity, nonce or authorization |
| `Attestation` | signed action/output digests and provenance | Integrity/authenticity evidence | Reuse attestation mechanism for artifact digests, not for truth claims |
| `noryx7_runtime/engine.py` | canonical JSON hashing, scheduler, adapter, signer, identity and authorization | Existing execution/data plane | Do not move NEXUS parsing or LLM inference into privileged runtime |

## 4. Confirmed gaps and non-findings

The following are directly visible in inspected code:

1. Meaning-bearing content is often plain text: `AgentInput.content`, `Intent.text`, `Hypothesis.statement`, `Evidence.claim`, `DomainAssessment.conclusion`, and `PlanStep.objective`.
2. Generic mappings and `Any` appear in context, memory, task input, action parameters and runtime parameters. These are useful extension points but are not a semantic type system.
3. Existing canonical JSON hashing in the runtime is a deterministic digest helper for a constrained runtime payload. It is not a semantic canonicalization standard and does not establish equivalence of meaning.
4. Existing identity, provenance, attestations, ActionGate and admission checks protect execution boundaries. They do not independently prove that two natural-language or multimodal descriptions have identical meaning.
5. Existing metacognition validates pipeline structure and evidence linkage. It is not a general formal theorem prover.
6. Existing evidence/confidence/uncertainty fields are useful, but numeric confidence is not a substitute for provenance, proof status, calibration or epistemic semantics.

The following were **not located in the inspected files**, but cannot be declared absent from every branch or uninspected module:

- A single versioned semantic type registry and ontology governance protocol.
- A typed concept/relation graph with canonical identifiers and constraints.
- A versioned semantic message envelope and capability-safe negotiation.
- A semantics-preserving parser/compiler boundary.
- A verifier that checks referential integrity, type constraints, provenance continuity and meaning-preserving transformations.
- A controlled schema/vocabulary evolution and migration protocol.
- A multimodal common representation with source coordinates, units, temporal alignment and modality-specific uncertainty.
- A general causal/counterfactual representation with explicit assumptions.
- A conformance suite that tests semantic round-trip and cross-agent interpretation equivalence.

## 5. NEXUS design: three distinct layers

NEXUS must not collapse syntax, meaning and execution into one format.

### 5.1 NEXUS-IR — canonical semantic intermediate representation

A typed, versioned, language-neutral graph of claims, entities, events, quantities, relations, goals, constraints and evidence. The IR is the semantic source of truth for NEXUS artifacts; it is not executable code and grants no authority.

Minimum node fields:

- globally scoped stable identifier;
- semantic type identifier from a versioned registry;
- typed value or references (exactly one according to the type definition);
- source/provenance references;
- epistemic status and supporting evidence references where applicable;
- validity interval / observation time when applicable;
- unit and coordinate/reference frame for physical quantities;
- schema and vocabulary version.

Minimum edge fields:

- stable relation type identifier;
- source and target node identifiers;
- directionality and cardinality rules;
- qualifiers (time, modality, conditions) as typed values;
- provenance and epistemic status where the relation is inferred rather than directly asserted.

The graph may contain cycles where the ontology permits them. Validation must reject dangling references, duplicate identifiers, unknown mandatory types, invalid cardinalities, incompatible units and undeclared relation types. It must not assume every semantic graph is a tree or DAG.

### 5.2 NEXUS-Wire — message and artifact exchange protocol

A transport envelope must be separate from the semantic graph. Minimum envelope fields:

- protocol version and message kind;
- message id, sender identity, recipient or audience;
- correlation id and causation/parent message id;
- creation time, expiry/deadline and replay identifier;
- payload media type, schema id/version and payload digest;
- provenance/attestation references;
- declared required capabilities (descriptive only; authorization still checked independently);
- size/resource budget and bounded parsing policy.

Transport authentication, signatures, principal identity, replay prevention and authorization must reuse existing trusted mechanisms. A valid signature means the artifact came from a key holder and was not altered; it does not mean its claims are true.

### 5.3 NEXUS-Surface — human authoring and inspection syntax

An optional readable DSL for debugging, authoring and review. It is not the canonical representation and is not required for agent-to-agent exchange. Natural-language input remains supported through an adapter. The DSL must compile to NEXUS-IR and round-trip to a normalized representation without silently dropping meaning.

## 6. Required semantic/epistemic model

NEXUS must distinguish at least:

- observed: directly measured or sourced observation;
- reported: asserted by a source, not independently verified;
- derived: logically or computationally derived with derivation record;
- formally_proven: checked proof artifact tied to an exact proposition and theory;
- simulated: output of a named model/run with assumptions and parameters;
- hypothesized: candidate claim awaiting validation;
- disputed: competing evidence/claims exist;
- unknown: not known from available evidence;
- undecidable_relative_to_theory: only when a specific formal theory and result justify this label.

Do not use a single confidence scalar as the status. Store confidence/calibration separately from provenance and epistemic status. A theorem checker can establish proof validity for an exact formal statement; it cannot by itself establish that the statement faithfully captures a source text or intended concept.

Object-level and meta-level claims must be typed separately. A proposition about a system must not be confused with a proposition about what that system can prove. FRL remains the proof/limits subsystem; NEXUS supplies typed propositions and proof-artifact references.

## 7. Canonicalization and semantic integrity

Canonicalization must be specified before any cross-agent digest/signature is relied upon.

Required rules:

1. Strict schema validation before canonicalization.
2. Unicode normalization (NFC) for identifiers and text fields where normalization is semantically permitted; preserve original source bytes/text separately.
3. Reject duplicate map keys and collisions introduced by normalization.
4. Deterministic key ordering and deterministic number encoding. Prefer integers or exact decimal/rational representations for quantities; reject NaN and infinities.
5. Explicit units, dimensions, coordinate frames and timezone semantics; never infer them from display strings.
6. Stable ordering only for semantically unordered collections. Preserve order where order is meaningful.
7. Explicit distinction between absent, null, empty and unknown.
8. Bounded depth, node count, edge count, string/byte length, numeric magnitude and parser CPU/memory.
9. Content digest over the canonical artifact plus schema/vocabulary identifiers; signatures/attestations remain separate.
10. Canonicalization version changes require explicit migration and cross-version test vectors.

Do not claim that byte-level canonical equality proves semantic equivalence. Semantic equivalence requires a declared equivalence relation and a verifier appropriate to the domain.

## 8. Integration points and authority boundaries

- **Ingress:** natural-language, API and multimodal adapters create untrusted candidate artifacts with source references. They do not create verified facts.
- **Contract verification:** validate NEXUS schema, types, limits, provenance references and version compatibility before planning.
- **Context:** attach immutable artifact references/digests to existing ContextSnapshot; do not create a parallel context store.
- **Decomposition/planning:** bind objectives and plan steps to typed goal/constraint references while retaining readable labels.
- **Hypothesis/simulation:** represent hypotheses and simulation outputs as typed claims with assumptions, model/version/run identifiers and evidence.
- **Universal Intelligence:** map Evidence and DomainAssessment to semantic claim/evidence nodes; preserve uncertainty and contradictions.
- **Agent Fabric:** exchange NEXUS-Wire messages only after existing identity, principal and skill checks. The message protocol cannot grant a skill or capability.
- **FRL:** accept explicit formal proposition/theory/proof-artifact references; proof result is scoped to exact statement, axioms, checker and build.
- **Metacognition/result admission:** verify identity, provenance, graph integrity, transformation lineage, required evidence and status transitions.
- **ActionGate/runtime:** receive only a bounded ActionSpec/ActionEnvelope projection. NEXUS content is data, never an executable instruction or authorization token. Existing ActionGate, policy, approval, replay and runtime checks remain mandatory.
- **Memory/audit:** persist content-addressed references, source lineage and schema versions; apply existing privacy, retention and execution-isolation rules.

## 9. Security and failure behavior

NEXUS parsers and compilers are attack surfaces. Treat every incoming artifact, model-produced graph, vocabulary extension and DSL program as untrusted.

Mandatory properties:

- fail closed on malformed, unsupported, ambiguous or over-budget input;
- no implicit network, filesystem, shell, code evaluation or tool invocation in parser/compiler;
- no executable payloads in semantic values;
- deny unknown critical fields; preserve or reject unknown optional fields according to explicit version policy;
- prevent schema confusion, type confusion, reference substitution, replay, downgrade and confused-deputy behavior;
- separate sender authentication from claim truth and authorization;
- sandbox expensive inference, conversion and formal checking outside privileged runtime;
- record artifact digest, schema/vocabulary version, source, transformation chain and verifier version;
- timeouts, missing verifiers, incomplete evidence and unavailable dependencies are not success;
- no hidden fallback from native representation to free-form text when validation fails.

Vocabulary evolution must be proposal → review → compatibility analysis → conformance tests → signed/versioned release → controlled rollout. Agents may propose new terms but cannot self-authorize global ontology changes.

## 10. Conformance and acceptance matrix

A first implementation is not accepted until deterministic tests cover:

### Structural validation
- valid minimal graph;
- missing/unknown required type;
- duplicate node/edge identifiers;
- dangling references;
- invalid relation direction/cardinality;
- incompatible value type, unit or coordinate frame;
- invalid timestamps/timezones;
- oversized/deep/cyclic adversarial structures within graph policy;
- duplicate keys and Unicode-normalization collisions.

### Canonicalization
- same semantic artifact serializes identically across repeated runs;
- key insertion order does not alter digest;
- semantically ordered arrays retain order;
- semantically unordered sets normalize deterministically;
- NaN/infinity and unsupported numeric forms reject;
- schema/vocabulary version changes alter artifact identity as specified;
- canonicalization test vectors pass across supported runtimes.

### Provenance and epistemics
- source reference survives parse → transform → serialize;
- observed, reported, derived, simulated, hypothesized and proven are never silently conflated;
- evidence removal invalidates dependent claims or marks them unsupported;
- a valid signature does not promote a claim to proven;
- formal proof status binds exact proposition, theory, axioms and checker artifact.

### Interoperability
- natural-language adapter creates candidate, not verified, claims;
- two agents with different internal models exchange one graph without loss of declared fields;
- unknown optional fields follow version policy;
- unknown critical fields reject;
- round-trip preserves declared semantic equivalence;
- unsupported modality/domain returns explicit unsupported/indeterminate result.

### Security and runtime
- oversized/deep payload rejects before unbounded allocation;
- malformed envelope, replay, expiry, wrong recipient and identity mismatch reject;
- semantic payload cannot bypass ActionGate or principal authorization;
- no parser/compiler code path invokes shell, eval, dynamic import, network or privileged tools;
- timeout, worker crash and missing checker fail closed;
- downgrade and schema-confusion attempts reject.

### Regression and compatibility
- all existing HYPERSYNTH, AgentFabric, UniversalIntelligence, ActionGate, runtime and audit tests remain green;
- existing TaskSpec/AgentInput/Intent/ActionEnvelope consumers continue to work through adapters;
- no frozen baseline or unrelated security fix is rewritten;
- deterministic build/test manifest records exact source commit and dependency versions.

## 11. Delivery sequence

**Phase 0 — inventory and contract freeze (current):** record existing interfaces, repository boundaries, compatibility rules and non-findings. No runtime behavior changes.

**Phase 1 — NEXUS-IR reference model:** implement immutable typed primitives, graph validation, schema registry interface and canonical serialization in an isolated package. No agent dispatch, tools, I/O or runtime privileges. Add exhaustive unit/property/fuzz tests.

**Phase 2 — adapters:** add optional typed references to existing task, agent, evidence, context and hypothesis flows without changing their legacy required fields. Prove compatibility with regression tests.

**Phase 3 — NEXUS-Wire:** add versioned envelope, identity/provenance binding, replay/expiry/size limits and cross-agent conformance. Reuse existing identity and attestation components.

**Phase 4 — FRL bridge:** map explicitly typed propositions and proof artifacts to the existing Gödel-aware FRL RFC. No claim promotion without a checked proof and reviewed specification.

**Phase 5 — multimodal and causal domains:** add domain-specific schemas only with units, reference frames, time alignment, source coordinates and domain validation. Do not claim a universal representation before these pass.

**Phase 6 — controlled vocabulary evolution:** governance, signed releases, migrations, compatibility tests and rollback.

## 12. Non-goals and explicit limits

NEXUS is not:
- a new orchestrator or autonomous authority;
- a replacement for natural language, Python, existing model tokenizers or the OS;
- a hidden chain-of-thought export format;
- a theorem prover by itself;
- a guarantee that different models assign identical meanings to every concept;
- a method for eliminating mathematical undecidability, incomplete evidence or physical uncertainty;
- a permission/capability system;
- a reason to bypass existing ActionGate, policy, identity, runtime or audit controls.

The objective is precise: reduce ambiguity and semantic loss, make representations inspectable and versioned, and make transformations/evidence verifiable within declared domains.

## 13. Audit status

- Confirmed: inspected source paths listed in §2.1 and repository README/crypto audit in §2.2.
- Confirmed: `noryx7-verified` currently describes itself as a partial crypto transfer, not a full source mirror.
- Not confirmed: exhaustive file-by-file scan of all directories, branches, historical commits, generated files and external services.
- Not confirmed: runtime behavior of NEXUS (not implemented in this artifact).
- Not claimed: production readiness, semantic equivalence across arbitrary models, or perfect correctness.

**Decision:** proceed with an isolated NEXUS-IR reference implementation only after this interface map and acceptance matrix are reviewed. Keep all existing authority and execution boundaries intact.
