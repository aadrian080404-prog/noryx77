# NORYX7

NORYX7 is an experimental bounded agentic AI architecture for coordinating models, memory, tools, planning, reasoning, verification and autonomous task execution.

## Current Foundation

The `noryx7-foundation` branch now contains a concrete HYPERSYNTH cognitive-kernel implementation rather than only an architectural specification.

### HYPERSYNTH execution pipeline

```text
INPUT
  ↓
PERCEPTION / CONTRACT VERIFICATION
  ↓
CONTEXT ACQUISITION
  ↓
TASK DECOMPOSITION
  ↓
PLANNING + PLAN VERIFICATION
  ↓
HYPOTHESIS GENERATION + VERIFICATION
  ↓
INTERNAL SIMULATION + VERIFICATION
  ↓
RESOURCE ALLOCATION
  ↓
ACTION GATE / POLICY / SECURITY
  ↓
AGENT EXECUTION
  ↓
RESULT ADMISSION + VERIFICATION
  ↓
CROSS-CHECK / CONSENSUS
  ↓
OUTPUT VERIFICATION
  ↓
METACOGNITION SUMMARY
  ↓
MEMORY UPDATE + AUDIT
```

## Safety properties

* bounded planner and runtime action budget;
* explicit task, plan, action and result contracts;
* deny-by-default policy/security boundaries;
* fail-closed handling of routing, planning, decomposition and execution failures;
* provenance checks linking agent results to planned steps;
* consensus rejection on conflicting agent outputs;
* audit events for major cognitive/runtime transitions;
* deterministic acceptance tests for success and failure paths.

## Development principle

NORYX7 initially uses existing AI models/agents behind explicit contracts instead of attempting to train a frontier model from scratch. HYPERSYNTH is the orchestration and verification kernel around those resources.

The current implementation is an engineering prototype. A green test suite validates the implemented contracts; it does not by itself establish production readiness, frontier-model capability, or real-world autonomy.

## Version

NORYX7 foundation — HYPERSYNTH kernel stage
