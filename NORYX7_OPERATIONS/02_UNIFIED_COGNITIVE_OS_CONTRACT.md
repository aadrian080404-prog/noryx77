# NORYX7 — Unified Cognitive Operating System Contract

## Purpose

NORYX7 is one operational cognitive system. Chat, cognition, runtime, agents, model routing, memory, security, verification, web, offline execution and external actions are not independent products. They are capabilities of one execution fabric.

## Canonical request lifecycle

```text
USER / CHAT
  -> authenticated session
  -> canonical execution identity
  -> perception + contract verification
  -> context acquisition
  -> task decomposition
  -> capability selection
  -> planning
  -> plan verification
  -> hypothesis generation + verification
  -> internal simulation + verification
  -> resource/model/agent routing
  -> authorization + identity + security gate
  -> capability/tool execution
  -> result admission
  -> result verification
  -> cross-check / consensus
  -> metacognition
  -> memory/state persistence
  -> provenance/audit
  -> gateway response
  -> CHAT
```

A required boundary may not be silently bypassed. If a capability is unavailable, the system must return an explicit fail-closed state rather than fabricate completion.

## External action model

External capabilities include, at minimum:

- `flights`
- `payments`
- `contracts`
- `bureaucracy`
- `insurance`

The capability fabric identifies the intended capability from the request and the planner emits an explicit action type. External capabilities are high-risk and are therefore promoted to a high-risk `ActionSpec` at the tool boundary and require authorization before a provider can execute.

Provider adapters are deliberately separate from cognitive reasoning. They receive the canonical `execution_id`, an idempotency key derived from it, and an explicit operation. Provider responses must return the same execution identity and an explicit verified/accepted status.

## What “works” means

A capability is not considered operational merely because a class, endpoint or adapter exists.

It is operational only when:

1. a real chat request selects it;
2. the request remains inside the canonical execution identity;
3. planning and verification admit the action;
4. authorization/security gates are crossed;
5. the real provider executes it when configured;
6. the result is identity-bound and verified;
7. the final result returns through the same gateway/chat path;
8. an end-to-end test proves the complete lifecycle.

## Current external-provider truth

The generic provider adapter is implemented, but real flights/payments/contracts/bureaucracy providers are intentionally **not claimed as live** until their HTTPS endpoints and credentials are configured. This is a security requirement, not a frontend limitation.

Until then, NORYX7 must fail closed with a provider/authorization state and must never claim that a purchase, payment, booking, contract signature or government submission occurred.
