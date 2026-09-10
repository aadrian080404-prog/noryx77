# NORYX7 — WAVE MASTER PLAN

Status: PRE-REGISTERED — planning only. No wave is considered implemented by this document.

## Rule
Wave 10 must close first. A wave can advance only after its real repository implementation, integration checks, deterministic tests, compileall, and required end-to-end checks pass. Never weaken security or modify tests to obtain green.

## Wave sequence

| Wave | Name | Primary objective | Closure gate |
|---|---|---|---|
| 10 | End-to-End Closure | Prove existing architecture is genuinely connected locally and hosted | full pytest exit 0 + local/hosted E2E |
| 11 | Multimodal & Voice Fabric | Connect voice, vision and multimodal boundaries to the same identity/runtime/security path | text/voice/vision contract E2E |
| 12 | External Capability Fabric | Real payment, travel, insurance and other external adapters behind explicit credentials/policy | sandbox adapter E2E + fail-closed tests |
| 13 | Distributed Resource & Edge Fabric | Connect resource routing, edge/cloud execution and model routing to one execution contract | routing consistency + failover E2E |
| 14 | Offline & Knowledge Fabric | Make offline research, annotation, knowledge retrieval and online fallback coherent | offline/online parity + provenance |
| 15 | Memory Fabric | Complete L0-L5, suspended/distributed memory, retention and audit semantics | persistence/recovery/privacy E2E |
| 16 | Continuous Agent Runtime | Long-lived agents, scheduling, supervision, learning loops and bounded autonomy | lifecycle/fault/recovery tests |
| 17 | NORYX Browser & Device Fabric | Connect browser/mobile surfaces to canonical session, identity and runtime boundaries | browser-to-runtime E2E |
| 18 | Observability, Audit & Verification | Unified provenance, telemetry-safe audit, verification evidence and incident diagnostics | trace completeness + tamper tests |
| 19 | Scale, Concurrency & Performance | Million-case campaigns, concurrency, load, backpressure and resource budgets | deterministic scale gates + load evidence |
| 20 | Production Hardening & Release | Deployment, rollback, dependency, secrets, resilience and release certification | production-readiness checklist |

## Non-negotiable cross-wave contract

Every wave must declare:
1. input/output contracts;
2. identity and principal binding;
3. authorization/policy boundary;
4. capability/resource dependencies;
5. verification and provenance;
6. failure/recovery behavior;
7. persistence/audit implications;
8. deterministic tests;
9. E2E path proving the new structure is actually used;
10. explicit dependencies on earlier waves.

## Known current audit targets

The repository already documents a verified JARVIS/Core/Runtime vertical path and shared capability registry. It also explicitly states that remaining structures must be connected through real repository contracts rather than repeatedly testing already-verified layers.

Current known non-closure targets to investigate during Wave 10 include:
- semantic handling of `Chi è Adrian Aristodemo?`;
- browser `/api/chat` versus direct `/v1/execute` parity;
- hosted Render verification versus local verification;
- voice boundary exposure at the hosted web surface;
- external providers intentionally fail-closed until configured;
- optional JARVIS execution configuration;
- provider/model/runtime representation consistency;
- hidden integration seams where a component exists but is not traversed by the canonical path.

## Research protocol

For every wave perform a dual audit:
- visible failures: UI/API/runtime errors, broken states, wrong responses;
- invisible failures: dead imports, unused adapters, bypass paths, duplicated state, stale identity, contract drift, fallback masking, unreachable code, missing persistence, missing provenance, untested concurrency, configuration-dependent behavior.

The objective is not to maximize the number of files changed. The objective is to prove that each architectural claim corresponds to a live executable connection.
