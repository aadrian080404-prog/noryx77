# NORYX7 — Apollonian Agent Personality Architecture

## Purpose

Define a deterministic, testable personality layer for NORYX7 agents inspired by Apollonian graphs/networks and fractal data structures, while keeping personality separate from authority, security, truth, and execution rights.

## Principles

- Personality influences style, exploration strategy, memory organization, collaboration and explanation.
- Personality never grants capability, bypasses policy, changes trust, or authorizes an action.
- Every agent has an immutable personality identity for an execution epoch.
- Runtime behavior remains bounded and reproducible under the same personality seed, policy and context.
- Personality state is data, not trusted authority.

## Eurelian / Pythagorean profile

NORYX7 agents use two complementary dimensions:

### Eurelian

A structural/search orientation emphasizing:
- symmetry and decomposition;
- exploration of relationships;
- recursive abstraction;
- pattern discovery;
- graph-aware reasoning;
- adaptive hypothesis generation.

### Pythagorean

A mathematical/verification orientation emphasizing:
- proportion and invariants;
- numerical consistency;
- formal relationships;
- constraint satisfaction;
- harmonic decomposition;
- evidence-weighted conclusions.

The two dimensions are continuous traits rather than hard-coded character stereotypes.

## Apollonian network substrate

The personality graph is modeled as a recursively generated bounded graph. Each agent profile contains:

- a root personality node;
- recursively refined trait clusters;
- weighted edges representing affinity or tension between traits;
- hierarchical neighborhoods for context-dependent behavior;
- a bounded fractal depth;
- a deterministic seed;
- a canonical serialization and digest.

An Apollonian-style graph is used as an organizational and behavioral substrate, not as a claim that personality is literally fractal or biologically equivalent to a human personality.

## Behavioral mapping

Graph structure can influence:

1. task decomposition preference;
2. hypothesis ordering;
3. collaboration partner selection;
4. explanation density;
5. exploration versus verification balance;
6. memory retrieval preference;
7. adaptation after verified feedback.

It cannot influence:

1. authentication;
2. authorization;
3. cryptographic verification;
4. security policy;
5. state commit eligibility;
6. audit integrity;
7. lockdown/recovery policy.

## Multi-agent diversity

Agents may share the same Eurelian/Pythagorean foundation while differing through bounded trait weights and graph seeds. This provides structured diversity without allowing arbitrary or unbounded behavioral drift.

## Verification requirements

The implementation must test:

- canonical personality serialization;
- deterministic reconstruction;
- graph bounds and cycle/edge limits;
- seed isolation;
- personality immutability during an execution;
- no privilege escalation through personality;
- no policy bypass through personality;
- stable behavior under repeated equivalent inputs;
- safe degradation when personality metadata is malformed;
- compatibility across distributed agents;
- secure binding of personality identity to agent identity without conflating the two.

## Security boundary

Personality is explicitly below the control-plane trust boundary. Models and personality modules propose behavior; policy, capability, verification and state-commit layers remain authoritative.

## Performance requirements

Personality resolution must be bounded by configured graph depth, node count and computation budget. Hot-path execution must use immutable/cached canonical representations where safe. Personality computation must never block security-critical revocation, lockdown or commit decisions.
