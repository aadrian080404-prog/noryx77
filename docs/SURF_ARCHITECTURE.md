# NORYX7 SURF — System Understanding & Reverse Engineering Fabric

SURF is a bounded, evidence-grounded capability of the NORYX7 Cognitive Kernel. It reconstructs authorized systems from observable artifacts and behavior, verifies hypotheses, compares alternative designs, and supports improvement without treating implementation copying as a goal.

## Pipeline
Authorization/scope -> artifact integrity -> static + dynamic + behavioral analysis (parallel) -> evidence fusion -> system graph -> hypotheses + counter-hypotheses -> controlled experiments -> verification -> behavior/architecture model -> comparative simulation -> improvement candidate -> policy/security gate -> implementation -> regression verification -> metacognition/audit.

## Evidence states
observed, inferred, hypothesized, verified, contradicted, unknown.

Unknown is never promoted to fact without evidence.

## Core objects
ArtifactManifest, EvidenceRecord, Observation, SystemNode, SystemEdge, SystemGraph, HypothesisRecord, CounterHypothesis, Experiment, BehaviorModel, InterfaceModel, ArchitectureModel, ImprovementCandidate, SURFAssessment, SURFReflection.

## Parallel specialist fabric
Artifact, Static, Dynamic, Behavioral, Interface, Evidence Fusion, Graph, Hypothesis, Counter-Hypothesis, Verification, Architecture and Improvement specialists are orchestrated by a bounded SURF Director through Agent Fabric.

## Security invariant
SURF never receives implicit authority from its analytical role. Acquisition, execution, modification and external actions remain behind identity, authorization, policy, sandbox/resource and audit boundaries. Experiments require explicit authorization and sandboxing.

## Self-analysis
SURF may analyze NORYX7 itself to compare declared contracts, implementation structure and observed runtime behavior. Discrepancies become verification failures or audit findings, not silently corrected assumptions.

## Non-copying principle
SURF extracts capabilities, behavior, contracts, constraints and failure modes. An improvement candidate is a new design evaluated against requirements; source-code or proprietary implementation copying is not an architectural objective.

## Benchmark
NORYX7-SURF-Bench should measure structural recovery, behavioral recovery, false claims, contradiction detection, reproducibility, verification rate, resource consumption and regression safety across source, compiled, optimized, distributed and self-analysis fixtures.
