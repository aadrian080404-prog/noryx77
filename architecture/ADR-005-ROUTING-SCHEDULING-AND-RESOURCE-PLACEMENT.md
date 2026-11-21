# ADR-005 — Separation of model routing, agent routing and resource placement

**Status:** Proposed architecture decision; source-inspected, not implemented  
**Date:** 2026-11-21  
**Scope:** provider selection, agent allocation, scheduling and distributed resource placement

## Context and observed source

The current architecture uses routing and scheduling concepts at different layers:

- `core/runtime.py` constructs `ResourceRouter` and registers deterministic and optional LLM-backed agents.
- `core/operational_fabric.py` uses the router to resolve agents and a supervisor to select/admit work.
- `core/agent_fabric.py` selects eligible agents by identity, skill and principal authorization.
- `noryx7_runtime/engine.py` uses a deterministic `Scheduler` to order dependency-constrained action steps.
- `noryx7_runtime/scheduler.py` performs topological scheduling; it does not choose a model provider or compute placement.
- Performance and distribution are separate canonical planes (P17 and P13).

The term “routing” currently risks conflating model/provider choice, agent selection, action dispatch and node placement.

## Decision proposal

Define four distinct decisions, each with one owner:

1. **Model/Provider Routing (MPR):** selects an inference provider/model tier for a cognitive subtask based on modality, quality, latency, cost, privacy, availability and policy. It returns a provider binding; it never grants tools or external action authority.
2. **Agent Allocation (AA):** selects a trusted agent identity and skill manifest for a task. It returns a bounded delegation lease; it does not select infrastructure placement.
3. **Plan Scheduling (PS):** orders steps according to dependencies, deadlines, priorities and resource estimates. It returns a deterministic execution order or a declared scheduling failure.
4. **Resource Placement (RP):** selects device/edge/cloud execution location based on data residency, hardware, locality, capacity, trust zone, energy, cost and availability. It returns a placement lease, not an action authorization.

A fifth component, **Action Dispatch (AD)**, carries an already authorized envelope to its target adapter and reports dispatch status. AD does not re-plan or widen scope.

## Canonical decision flow

```text
Task contract
  -> MPR: which model/provider (if inference needed)?
  -> AA: which trusted agent owns this task?
  -> PS: in what dependency-safe order?
  -> RP: where may this workload run?
  -> Capability Broker + ActionGate: what actions are permitted?
  -> AD: dispatch only the authorized envelope
  -> Result Admission + State Authority
```

Not every task needs every stage. The coordinator records which decisions were required, skipped and why.

## Precedence and conflict rules

- Security, privacy, residency and authorization constraints are hard constraints, not weighted preferences.
- Among eligible options, optimization may consider latency, cost, energy, throughput and quality.
- A lower-cost provider cannot override a no-cloud or data-locality constraint.
- A placement decision cannot change agent identity or action scope.
- A model/provider cannot request a capability merely by returning a tool call.
- Scheduler output cannot reorder across unmet dependencies.
- Resource exhaustion produces backpressure, bounded degradation or rejection; never unbounded queue growth.
- Failover requires a fresh eligibility and trust check; stale cached provider/agent/placement decisions cannot authorize dispatch.

## Budgets and fairness

A single task budget should be decomposed into explicit envelopes:
- inference tokens/time/cost;
- agent CPU/memory/concurrency;
- tool/action count and risk;
- network bytes and remote calls;
- storage and retention;
- energy/thermal envelope;
- deadline and cancellation propagation.

Budgets are charged to a principal/tenant and correlated execution. Admission reserves bounded capacity; cancellation releases only resources that are actually releasable. Fairness and priority policies must be explicit, auditable and resistant to starvation.

## Alternatives considered

- One universal router deciding model, agent, tools and node: rejected; too much authority and opaque failure handling.
- Provider routing only, with placement left implicit: rejected; violates edge/offline/residency requirements.
- Four specialized decisions coordinated by SRC: proposed.

## Open questions

- Which existing `ResourceRouter` responsibilities are provider routing versus agent endpoint resolution?
- Where does current model-fabric tier selection end and physical placement begin?
- Which resource budgets are enforced at admission versus during execution?
- What are the default fairness classes for interactive, background, safety-critical and offline tasks?

## Acceptance evidence before architecture freeze

- Explicit ownership matrix for MPR, AA, PS, RP and AD.
- Hard-constraint precedence and failover semantics.
- Budget schema and accounting owner.
- Backpressure, cancellation, fairness and starvation policies.
- Traceable decision records for provider, agent, scheduler and placement choices.
