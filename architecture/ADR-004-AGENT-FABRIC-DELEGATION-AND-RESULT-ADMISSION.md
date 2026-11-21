# ADR-004 — Canonical agent fabric, delegation and result admission

**Status:** Proposed architecture decision; source-inspected, not implemented  
**Date:** 2026-11-21  
**Scope:** agent identity, skills, supervision, delegation, collaboration and trust

## Context and observed source

Relevant inspected components:

- `core/agent_fabric.py`: bounded native-agent registry, agent identity/skills, principal binding and authorization callback.
- `core/operational_fabric.py`: supervisor/router path, availability checks, dispatch and result admission.
- `core/operational_runtime.py`: installs `OperationalAgentFabric` as HYPERSYNTH supervisor and starts required primary/secondary hosted agents.
- `core/hypersynth_runtime.py`: collaboration capability invokes primary → secondary → primary and checks a reconciliation result.
- `core/agent_core.py`, `core/agent_skills.py`, `core/supervisor.py` and identity modules define adjacent responsibilities.

This indicates at least two fabric abstractions with distinct shapes. The architecture must clarify whether one is a native extension fabric and the other an operational execution fabric, or whether they are competing dispatch authorities.

## Decision proposal

Define one **Canonical Agent Fabric (CAF)** contract with six separable services:

1. **Agent Registry:** immutable agent ID, owner, implementation/version, public identity, lifecycle state and trust status.
2. **Skill/Capability Manifest:** declarative skills and required capability classes; a skill is not an authorization grant.
3. **Delegation Broker:** issues scoped, time-bounded, attenuated delegation tokens bound to principal, task, agent, resource and policy epoch.
4. **Supervisor/Allocator:** chooses eligible agents using declared skills, health, budget and task constraints; cannot widen authority.
5. **Execution Adapter:** invokes the selected agent within the permitted sandbox/resource envelope.
6. **Result Admission:** validates task binding, selected agent identity, schema, provenance, evidence, resource limits and verification policy before accepting output.

### Agent lifecycle

```text
DECLARED -> REGISTERED -> TRUSTED -> READY -> LEASED -> RUNNING
   |            |           |        |       |        |
   +----------> REJECTED / QUARANTINED / REVOKED <----+
                                      |
                           COMPLETED / FAILED
                                      |
                             RESULT ADMISSION
                                      |
                         ACCEPTED / PARTIAL / REJECTED
```

An agent's online status is operational health, not proof of trust. Trust can be revoked while an agent remains reachable.

## Delegation invariants

- The principal remains the source of authority; an agent cannot self-authorize.
- Delegation is narrower than the parent grant: fewer capabilities, narrower resource scope, shorter expiry and no privilege escalation.
- Each delegation binds a unique task/execution ID and policy epoch.
- Sub-delegation is disabled by default; if enabled, attenuation is mandatory and depth/budget bounded.
- Agent output is untrusted input until admitted.
- Consensus is not authorization and does not transform unsupported claims into evidence.
- A secondary agent's review is independent only when independence assumptions (model/provider, context, tools, source set) are declared.
- Agent failure, timeout or revocation cancels outstanding leases and blocks new actions.
- Agents cannot write durable state directly; they submit proposals/results to the state authority.

## Dispatch and admission protocol

```text
TASK + PRINCIPAL + POLICY
  -> eligible-agent set
  -> supervisor selection + reason
  -> attenuated delegation lease
  -> bounded agent execution
  -> signed/bound result envelope
  -> independent result admission
  -> state authority accepts or rejects
```

Selection and admission must be separate operations. A successful `run()` is not a successful task; the result must satisfy the receiving task contract.

## Native and hosted agents

Proposed compatibility mapping:
- `AgentFabric` is a candidate native-agent registry/dispatch adapter.
- `OperationalAgentFabric` is a candidate supervisor/operational-dispatch adapter.
- `AgentRuntime` is a hosted-agent lifecycle/health adapter.
- `ResourceRouter` is a candidate transport/agent endpoint resolver, not the authority source.
- `AgentCollaboration` is a workflow strategy over CAF, not a parallel trust system.

This mapping remains a proposal until all call sites and identity paths are inventoried.

## Alternatives considered

- Keep both fabrics as independent authorities: rejected due to ambiguous dispatch and result trust.
- Collapse all functions into one fabric class: rejected due to lifecycle, allocation and admission coupling.
- One canonical contract with specialized adapters/services: proposed.

## Open questions

- Does native `AgentFabric` dispatch serve production paths or only isolated subsystems?
- Which registry owns cross-runtime agent identity and key rotation?
- What independence guarantees can be made for primary/secondary verification?
- Which agent types may request tools, and which may only return proposals?

## Acceptance evidence before architecture freeze

- Agent identity and lifecycle state machine.
- Delegation token schema and attenuation rules.
- Unified eligibility/selection/admission contracts.
- Trust revocation and lease-cancellation semantics.
- Primary/secondary independence and consensus limitations.
- Complete inventory of all direct agent invocation paths and proof that privileged actions remain behind ActionGate.
