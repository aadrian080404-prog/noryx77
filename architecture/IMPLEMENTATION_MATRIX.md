# NORYX7 / HYPERSYNTH implementation matrix

| Boundary | Implemented component | Verification target |
|---|---|---|
| Ingress / identity | `core/contracts.py`, `core/identity.py`, `core/agent_context.py` | bounded IDs, principal/runtime binding, trusted key registry |
| Planning | `core/planning.py`, `core/decomposition.py` | typed plans, dependency validation, bounded steps |
| Policy / security | `core/policy.py`, `core/security.py`, `core/actions.py` | deny-by-default and action gating |
| Capability | `noryx7_runtime/capabilities.py` | explicit registration and single capability resolution |
| Scheduling | `noryx7_runtime/scheduler.py` | dependency ordering, cycle rejection, bounded execution |
| Secure execution | `noryx7_runtime/adapters.py` | adapter identity and capability boundary |
| Result integrity | `core/model_fabric.py`, `noryx7_runtime/attestation.py` | canonical digests, Ed25519 signatures, provenance binding |
| State | `noryx7_runtime/state.py` | signed append-only journal, runtime/principal/chain continuity |
| Recovery | `noryx7_runtime/recovery.py` | sequence, duplicate, identity, signature and provenance validation |
| Cognitive kernel | `core/hypersynth.py` | perception→context→planning→hypothesis→simulation→allocation→execution→verification→metacognition |
| Multi-agent trust | `core/agent_collaboration.py`, `core/agent_relationship.py`, `core/peer_execution.py` | signed/sealed evidence, replay and retargeting rejection |
| Cryptography | `core/crypto.py` | AES-256-GCM, HKDF-SHA256, authenticated metadata, strict size limits |

## Security invariant

A successful execution must have: a valid execution identity, an authorized action, a verified result, an intact cryptographic/provenance chain, and an accepted state transition. Failure at any boundary must fail closed.

## Verification order

1. Static structure and imports.
2. Unit and regression tests.
3. Full suite.
4. Adversarial mutation tests.
5. CI compile/type/dependency checks.
6. Review of changed contracts and trust boundaries.

A green suite is evidence for the tested invariants; it is not a claim of production security or unrestricted autonomy.
