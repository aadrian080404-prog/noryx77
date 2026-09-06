# NORYX7 — Machine-Inspired Systems

This design takes selected *functional ideas* associated with Finch's fictional Machine in **Person of Interest** and redesigns them as bounded, auditable NORYX7 subsystems. It is not an implementation of the fictional Machine and does not reproduce proprietary code or fictional capabilities.

## Systems introduced

### 1. Continuous event fusion
Ingest timestamped observations from explicitly authorized adapters and normalize them into a common event stream. Sources remain provenance-bound.

### 2. Relevance filtering
Rank events by severity and task-specific signals so NORYX7 can focus compute on what matters instead of processing everything equally.

### 3. Temporal relationship graph
Maintain a bounded graph of relationships between observations, devices, tasks or other permitted entities. Canonical graph snapshots are digestable and reproducible.

### 4. Anomaly detection
Compare current signals against bounded baselines and surface deviations for verification. An anomaly is a hypothesis, not proof of wrongdoing.

### 5. Predictive forecasting
Aggregate verified observations into bounded probability estimates over a declared horizon. Forecasts must carry evidence references and uncertainty; they never directly authorize action.

### 6. Scenario simulation
Feed relevant signals into HYPERSYNTH's existing hypothesis/simulation pipeline to compare possible futures and challenge assumptions before taking consequential actions.

### 7. Independent challenge / dissent
Use differently routed agents, including Eurelian and Pythagorean personalities, to challenge the primary hypothesis. Disagreement should trigger verification rather than automatic selection of the majority.

### 8. Memory with provenance
Store useful observations with execution scope, provenance and audit linkage so future reasoning can distinguish remembered evidence from generated hypotheses.

### 9. Defensive tripwires
Security anomalies can raise a verification/containment signal. Lockdown, revocation and recovery remain controlled exclusively by the security/control plane.

## Hard boundaries

- No covert collection.
- No unauthorized device or account access.
- No autonomous mass surveillance.
- No person-level risk label is treated as fact from an anomaly score.
- No facial recognition or biometric identification is implied by this subsystem.
- No forecast directly triggers a high-impact action.
- No personality can change authority or security policy.
- All external observations require an authorized adapter and provenance.
- Sensitive operations require the existing capability and authorization gates.

## Runtime placement

```text
Authorized Event Adapters
        |
        v
[Event Normalizer] -> [Relevance] -> [Temporal Graph]
        |                    |
        +--------------------+----> [Anomaly Detector]
                                     |
                                     v
                              [Forecast Engine]
                                     |
                                     v
                              [HYPERSYNTH]
                           /       |        \
                     Hypotheses  Simulation  Dissent
                           \       |        /
                            [Verification]
                                  |
                         [Capability / Policy]
                                  |
                         [Secure Dispatch]
                                  |
                         [Attestation / Commit]
```

The implementation begins with deterministic, bounded event-fusion primitives. Deeper forecasting, simulation and continuous operation must be integrated only through existing verification, capability, audit and security boundaries.
