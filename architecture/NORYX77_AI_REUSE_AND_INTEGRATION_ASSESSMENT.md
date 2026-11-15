# NORYX77 — AI Reuse and Integration Assessment

**Assessment date:** 2026-11-15  
**Method:** static source inspection through GitHub; no source files modified and no test suite executed during this assessment.  
**Target:** integrate reusable NORYX7 foundations into the unified architecture without rewriting working code or importing unverified prototypes.

## Executive decision

**Decision: REUSE THE MAIN-BRANCH AI FOUNDATION, WITH ADAPTATION AND INTEGRATION GATES.**

The source repository `aadrian080404-prog/noryx77` already contains a meaningful AI stack:
- a real LLM provider path through OpenRouter;
- a provider-neutral Model Fabric;
- an LLM-backed agent and self-knowledge prompt context;
- a HYPERSYNTH cognitive kernel and runtime;
- primary/secondary agent collaboration;
- task contracts, planning, decomposition, verification, authorization and audit;
- user-understanding and interaction-context components;
- gateway and operational runtime entry points;
- extensive unit, adversarial and integration test files.

This is substantially more than a basic chatbot. The earlier chat experience is a valuable working proof of the model connection and conversational response path. However, the simplest chat script is not itself the complete HYPERSYNTH runtime, and the operational path still has gaps before it can be treated as the unified NORYX7 AI subsystem.

No code from the separate `noryx7-verified` repository should be imported wholesale. Its own audit notes identify unvalidated code, missing imports, stubs and serious security/design issues.

## 1. Repository and branch inventory

### 1.1 `aadrian080404-prog/noryx77`

- Public repository; default branch: `main`.
- Default branch head inspected: `7d900bc75843ea968aa5886d251dbfac83a5d93c`.
- The recursive tree contains 507 paths.
- The default branch contains the concrete model and runtime code listed below.
- `noryx7-foundation` exists at `93890fc2729a14119bec3ebf8ce5b313ca03fdb4`; its tree contains 72 paths and focuses on the bounded HYPERSYNTH kernel and tests. It does not contain the OpenRouter adapter, Model Fabric or real-chat entry point present on `main`.
- `Noryx7` is an older five-path branch with an early architecture README and a small state module; it is not the best integration source.
- The current default branch is older than many active feature branches and open PRs. Integration must therefore compare branch/PR code, not assume that every recent improvement is already in `main`.

### 1.2 `aadrian080404-prog/noryx7-verified`

- Private repository; default branch `main`; 93 paths.
- README says the repository is a separate verification/import workspace.
- README explicitly says the crypto block was transcribed from user-provided conversation text, is not a certified copy of the source repository, and its tests had not yet been run.
- `AUDIT_PRELIMINARY.md` says the crypto block is **not runtime-validated** and identifies unresolved Argon2 resource, constant-time, stub, KEM-format and dependency issues.
- `AUDIT_BLOCK2.md` says identity/consensus are present but not validated; it identifies simulated PUF limitations, concurrency/input-validation problems and permissive BFT defaults.
- `AUDIT_BLOCK3_4.md` identifies missing imports, stubs, vacuous checks, incomplete consensus, weak persistence and API authentication gaps.
- The repository must be treated as an audit/transcription workspace, not as an authoritative source of production-ready components.

**Decision:** retain its audit findings as review inputs; do not bulk-copy its implementation into the unified runtime.

### 1.3 `aadrian080404-prog/noryx7-`

- Private repository.
- Git tree endpoint returns 409: repository is empty.
- No implementation can be reused from this repository at present.

## 2. Reusable components in `noryx77/main`

| Component | Source paths | Assessment | Integration decision |
|---|---|---|---|
| Model provider abstraction | `noryx7_runtime/model_fabric.py` | Useful provider-neutral routing, capability matching, latency/cost metadata, bounded fan-out and result envelopes | Reuse; harden and align contracts |
| OpenRouter adapter | `noryx7_runtime/model_adapters/openrouter.py` | Real HTTP LLM connector with timeout, error handling and text response parsing | Reuse as one adapter; improve transport and metering |
| LLM-backed agent | `core/llm/agent.py` | Real model-backed agent, role/capability metadata, task prompt construction and output contract | Reuse; adapt to unified identity/capability interfaces |
| Model Fabric bridge | `core/llm/model_fabric_bridge.py` | Binds generation request to runtime/execution identity and disables tools at model boundary | Reuse; make binding cryptographically authenticated in operational config |
| Self-knowledge provider | `core/llm/self_knowledge.py` | Supplies bounded system identity, architecture, capabilities, limitations and scoped memory to model prompts | Reuse; make the registry the source of truth, not duplicated literals |
| HYPERSYNTH kernel | `core/hypersynth.py` | Multi-stage cognitive orchestration, decomposition, planning, hypotheses, simulation, routing, gates, verification and metacognition | Reuse as the cognitive kernel; review semantics and stage contracts |
| HYPERSYNTH runtime | `core/hypersynth_runtime.py` | Composes verifier, router, action gate, tools, memory, recovery and audit | Reuse; align with canonical durable runtime and Matrix policy |
| Operational runtime | `core/runtime.py`, `core/operational_runtime.py` | Registers model-backed agent, identity registry, HYPERSYNTH and primary/secondary collaboration | Reuse as an integration starting point; fix gateway composition |
| Agent collaboration | `core/collaboration.py`, `core/operational_fabric.py` | Primary → Secondary → Primary critique/reconciliation flow | Reuse as structured challenge, not independent consensus |
| User understanding | `core/user_understanding.py`, `core/interaction_context.py` | Consent-bound extraction of bounded topic/format/tone/workflow signals | Reuse selectively; extend with robust privacy, consent lifecycle and user controls |
| Memory | `core/memory.py`, `core/memory_hierarchy.py`, `core/secure_memory.py` | Existing local memory and hierarchy foundations | Reuse after aligning with durable encrypted and causal memory branches |
| Provider execution | `core/provider_router.py`, `core/provider_execution.py`, `core/provider_resilience.py`, `core/http_provider.py` | Provider selection, authorization boundary and resilience adapters | Reuse selectively; converge with Model Fabric rather than maintain competing routers |
| Gateway | `gateway/server.py`, `gateway/runtime_adapter.py` | HTTP session and execution boundary | Reuse after constructor/wiring correction and end-to-end validation |
| Tests | `core/test_hypersynth*.py`, `noryx7_runtime/test_model_fabric*.py`, `tests/test_operational_runtime.py`, `tests/test_provider*.py` | Meaningful deterministic/fake-provider and adversarial coverage exists | Preserve and run; add live-provider contract tests using mocked HTTP |

### Reuse classification

- **Directly reusable after test confirmation:** ModelRequest/ModelCandidate/FabricResult contracts, ModelFabric routing, LLMBackedAgent prompt/result boundary, SelfKnowledgeProvider, HYPERSYNTH phase structure, existing test fixtures.
- **Reusable with integration changes:** OpenRouter adapter, operational runtime, gateway, user-understanding, memory, provider resilience and collaboration.
- **Do not treat as proven capability:** universal intelligence labels, confidence values, simulation feasibility, consensus labels, million-scale claims or self-improvement claims unless the implementation and tests establish the property being claimed.
- **Do not import blindly:** the separate `noryx7-verified` crypto/consensus/cognitive blocks.

## 3. What the working chatbot proves — and what it does not

### 3.1 `noryx7_real_chat.py`

The inspected script:
- reads `OPENROUTER_API_KEY`;
- constructs `OpenRouterAdapter(model="openrouter/free")`;
- creates a `ModelFabric`;
- wraps it in `ModelFabricBridge`;
- constructs `LLMBackedAgent`;
- submits a `TaskSpec` for each user message;
- prints the model-backed answer.

This proves the code contains a real provider-backed conversational path. It is not merely a static mock in that script.

But that script also explicitly states:
- tools are disabled;
- the LLM has no execution authority;
- each user message is sent as a fresh task;
- it does not maintain a conversation message-history list or load prior turns into the next task.

Therefore this script is a **provider smoke/chat entry point**, not the complete NORYX7 conversational product.

### 3.2 `noryx7_operational.py` and `noryx7_bootstrap.py`

These are more important integration candidates:
- they construct the real OpenRouter-backed Model Fabric;
- create `OperationalNORYXRuntime`;
- require Primary and Secondary agents;
- execute requests through `run_hypersynth`;
- support an optional SQLite state-journal path;
- `noryx7_bootstrap.py --self-test` uses a fake model to check internal wiring and fail-closed behavior.

The self-test is not a live OpenRouter test. The operational CLI is a real-provider path when valid credentials and network access are configured, but no live call was performed during this static assessment.

### 3.3 The current Primary/Secondary limitation

`LLMBackedAgent._bootstrap_secondary` creates a distinct agent identity and role, but both Primary and Secondary receive the same `model_fabric` instance. The collaboration protocol therefore gives us different prompts and a useful critique/reconciliation sequence, but not independent model/provider evidence.

It must not be described as Byzantine consensus or independent multi-model verification. For stronger review, the Agent Fabric should support explicit role-specific model policies, separate providers/models where available, and provenance that identifies shared provider/model lineage.

## 4. Important integration gaps and defects to resolve

### G1 — Gateway default construction mismatch

- `gateway/runtime_adapter.py` defaults to `OperationalNORYXRuntime()`.
- `core/operational_runtime.py` explicitly raises `ValueError("model_fabric_required_for_operational_agents")` when no Model Fabric is supplied.
- `gateway/server.py` defaults to `RuntimeAdapter()`.

Therefore the default gateway construction path is inconsistent and can fail before serving requests unless a runtime adapter with a configured model fabric is injected.

**Required fix:** introduce one explicit composition root/factory that loads validated provider configuration and builds the canonical runtime; make missing provider configuration produce a controlled degraded/disabled state or clear startup error. Never silently create a fake production provider.

### G2 — Cross-turn conversation memory is not demonstrated

- `noryx7_operational.py` generates a new `execution_id` for each user turn.
- `SelfKnowledgeProvider._safe_memory` queries memory using that exact execution ID.
- This is execution-scoped memory, not a conversation/session memory contract.
- The simple real-chat script has no history buffer at all.

**Required fix:** add a conversation/session ID distinct from execution ID, explicit owner/tenant scope, bounded turn history or retrieval, retention/forgetting controls, encryption and prompt-injection-safe treatment of retrieved content. Never use a global unscoped memory pool.

### G3 — Model Fabric integrity binding is optional

- `ModelFabric` supports a `binding_key` of at least 32 bytes and validates request/result envelopes.
- The operational constructors inspected instantiate `ModelFabric([adapter], runtime_id=...)` without `binding_key`.
- In that configuration, result validation is deterministic digest consistency, not a keyed authenticity guarantee.

**Required fix:** inject a runtime-scoped key from the canonical key lifecycle/KMS boundary, bind request and result to model/provider identity, execution, policy version and prompt/data classification. Key rotation/revocation must be supported. Do not store raw key material in repository configuration.

### G4 — Primary/Secondary are not independent witnesses

Both roles use the same Model Fabric and normally the same configured OpenRouter model route. Different role prompts do not create statistical or operational independence.

**Required fix:** record provider/model/version/route lineage and require distinct trust domains for any claim of independent corroboration. If only one provider is available, label the result as same-provider self-critique, not consensus.

### G5 — Model economics are placeholders

The OpenRouter adapter reports `cost_per_call = 0.0` and fixed `expected_latency_ms = 5000.0`. These values are not live metering. The current response parser does not expose actual usage/cost to the Model Fabric.

**Required fix:** parse provider usage where available, reconcile against provider billing/usage data, track actual latency and distinguish unknown cost from zero cost. Cost ceilings must fail closed or reserve a safe worst-case estimate when usage is unknown.

### G6 — Provider transport hardening

The adapter has a positive timeout check and handles HTTP/URL/timeout/JSON/provider errors, but the inspected code reads the entire response body without a configured byte ceiling and uses the standard URL opener without an explicit redirect policy. Its timeout validation should also reject NaN/infinity/booleans consistently.

**Required fix:** bounded response reads, strict HTTPS/host allowlist, redirect rejection or explicit same-origin policy, content-type and schema checks, request/response size caps, retry budget, rate limiting, cancellation and secret-safe diagnostics. Keep test-only local HTTP exceptions isolated from production configuration.

### G7 — Verification is primarily structural

The LLM agent's result verifier checks that the output is non-empty and structurally valid. This is useful for admission, but it does not prove factual correctness. HYPERSYNTH's internal hypothesis/simulation stages are bounded software checks; they do not constitute external empirical verification unless connected to suitable tools/evidence.

**Required fix:** separate schema/identity/provenance validation from factual evidence verification. Attach citations, source records, tool receipts or reproducible test outputs where the task requires factual proof. Calibrate confidence; never treat a model-generated score as ground truth.

### G8 — The simplest chat script bypasses the cognitive runtime

`noryx7_real_chat.py` calls `LLMBackedAgent.run(task)` directly. It does not call `OperationalNORYXRuntime.run_hypersynth`.

**Required fix:** keep the script as a provider smoke test only. The canonical product interface must enter through the session/gateway and canonical operational runtime, not create a second parallel chat architecture.

### G9 — The test suite is not live-provider evidence

The repository contains useful tests for Model Fabric and operational runtime. The operational-runtime tests use a fake model adapter, and the bootstrap self-test also uses a fake model. These validate wiring and deterministic behavior, not live OpenRouter connectivity, provider billing, rate limits or current model availability.

**Required fix:** maintain hermetic fake-provider tests and add separately marked live-provider smoke tests that run only with explicit credentials and budget limits. Record the tested commit SHA, provider/model ID, timestamp, usage and result. Never expose API keys in logs.

## 5. Recommended integration target

The intended target should reuse the existing NORYX77 components under the unified P00–P22 architecture:

```text
NORYX Browser / Android / Web / Voice
                 |
         Authenticated Session
                 |
        Canonical Gateway / API
                 |
     Identity + Consent + Policy
                 |
       HYPERSYNTH Cognitive Kernel
        /       |        \
   Memory   TaskGraph   Evidence
      |        |           |
      +---- Agent Fabric --+
                 |
      Model Fabric / Provider Adapters
                 |
        LLMs (local / edge / cloud)
                 |
        Structured Agent Results
                 |
      Independent Evidence Verification
                 |
      ActionGate / Capability Runtime
                 |
       Sandboxed Tool Execution
                 |
         Audit + State Journal
                 |
       Response + Memory Commit
```

### Integration mapping to P00–P22

| Unified portfolio | Existing source to reuse |
|---|---|
| P00 Contracts | `core/contracts.py`, `noryx7_runtime/model_fabric.py`, `core/interaction_context.py` |
| P01 Identity | `core/identity.py`, `core/agent_identity.py`, `core/agent_runtime.py` |
| P02 Authorization | `core/actions.py`, `core/action_gate.py`, `core/policy.py`, `core/security.py` |
| P03 HYPERSYNTH | `core/hypersynth.py`, `core/hypersynth_runtime.py`, `core/reasoning.py`, `core/planning.py` |
| P04 Agent Fabric | `core/agent_fabric.py`, `core/operational_fabric.py`, `core/collaboration.py` |
| P05 Model Fabric | `noryx7_runtime/model_fabric.py`, `core/llm/agent.py`, `core/llm/model_fabric_bridge.py`, `noryx7_runtime/model_adapters/openrouter.py` |
| P06 Memory | `core/memory.py`, `core/memory_hierarchy.py`, `core/secure_memory.py`, `core/llm/self_knowledge.py` |
| P07 Runtime | `core/runtime.py`, `core/operational_runtime.py`, `core/agent_runtime.py` |
| P08 Interface | `gateway/`, `jarvis/`, `noryx-browser/`, `web/` |
| P12 Verification | `core/verification.py`, HYPERSYNTH adversarial tests, Model Fabric tests |
| P19 Operations | `noryx7_bootstrap.py`, workflow files, runtime health and audit components |

## 6. Proposed implementation sequence

1. **Preserve the working provider path.** Do not rewrite OpenRouterAdapter, ModelFabric or LLMBackedAgent before their existing tests are run.
2. **Create a canonical composition factory.** One supported way to configure local/edge/cloud providers, runtime ID, key lifecycle, limits, audit and identity.
3. **Fix gateway construction.** Ensure authenticated requests reach the configured operational runtime.
4. **Add session-scoped memory.** Separate conversation ID, execution ID and tenant/owner identity.
5. **Unify agent/model routing.** One canonical routing contract; no competing ProviderRouter and ModelFabric decisions without a defined boundary.
6. **Make model provenance authentic.** Inject runtime-scoped key references and verify result envelopes at admission.
7. **Make critique independence explicit.** Same-provider critique is useful but must be labeled accurately; add role-specific routing when more than one independent provider/model is configured.
8. **Harden provider economics and transport.** Meter cost, bound responses, constrain redirects, enforce timeouts and cancellation.
9. **Run all existing focused tests.** Then add end-to-end tests through gateway → session → HYPERSYNTH → LLM agent → Model Fabric → verification → response.
10. **Run controlled live smoke tests.** Only after configuration and budget limits are explicit; record evidence and never assume provider availability.

## 7. Evidence and file fingerprints inspected

Selected `noryx77/main` file SHAs:
- `core/hypersynth.py`: `187699d6e0945a2b1e8a9b194cd9001b1af8cd9f`
- `core/hypersynth_runtime.py`: `8df911b42f558274e2e560be66846a2dba4c35e9`
- `core/llm/agent.py`: `c2dc54757bb516ced4e36fd7590f675ba1a74475`
- `core/llm/model_fabric_bridge.py`: `544dd80facf249278adbb797b276f82935564305`
- `core/llm/self_knowledge.py`: `9a8a7683776c9e931ebe74c3b299bb596fcf053f`
- `noryx7_runtime/model_fabric.py`: `abb8bd9bb3217fff967e898afbdc491eb5082f45`
- `noryx7_runtime/model_adapters/openrouter.py`: `f1b6867807feec57ed585acef246ae92acf3dbc3`
- `noryx7_real_chat.py`: `923a9f9497337a706c8be6e221a26763ab0b24e2`
- `noryx7_operational.py`: `72300445c4c3cb8e18ae94f0226c2246a069d368`
- `core/operational_runtime.py`: `0106879b43b8de90a87a11ca9c361be72ab37072`
- `core/runtime.py`: `454f90e6b06ca6f013e325640a16d349b18797ae`
- `gateway/runtime_adapter.py`: inspected; default construction calls `OperationalNORYXRuntime()` without required model fabric.

Selected test files inspected:
- `noryx7_runtime/test_model_fabric.py`
- `noryx7_runtime/test_model_fabric_execution_binding.py`
- `core/test_hypersynth_acceptance.py`
- `core/test_hypersynth_adversarial.py`
- `tests/test_operational_runtime.py`
- `tests/test_http_provider_e2e.py`

## 8. Final verdict

**The existing NORYX77 AI code is valid as an integration foundation and should be reused.** The best value is in the actual Model Fabric, LLM-backed agent, HYPERSYNTH kernel/runtime, operational runtime and tests.

The right strategy is not to copy the whole repository or rebuild its AI. It is to preserve the working LLM path, make the canonical runtime use it consistently, fix the identified seams, and connect it to the newer identity, authorization, encrypted/causal memory, durable audit, sandbox and Matrix work already being developed.

This is a static assessment of source and repository metadata. It does not claim that the current deployed service is live, that all tests pass, or that the entire AI stack is production-ready.
