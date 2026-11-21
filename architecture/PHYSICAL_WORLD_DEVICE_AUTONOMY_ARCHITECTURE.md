# NORYX7 — Physical World, Device and Autonomy Architecture

**Status:** proposed architecture; implementation and verification deferred  
**Parent:** Global Architecture Closure Program  
**Consumers:** Device/Edge Fabric, MIRROR WORLD, HYPERSYNTH, Runtime, Identity and Safety

## 1. Mission

Define how NORYX7 may observe, model and, where explicitly authorized, affect physical devices and infrastructure. The architecture separates perception, planning, simulation, authorization, actuation and post-action observation. A digital twin is not an actuator, and an AI-generated plan is not permission to move hardware.

## 2. Operating modes

- **OBSERVE:** read approved sensor/device data; no actuation.
- **MODEL:** build or update a digital representation.
- **SIMULATE:** run hypothetical changes in MIRROR WORLD.
- **RECOMMEND:** present an intervention proposal without execution capability.
- **SUPERVISED ACT:** execute a bounded action after explicit human approval.
- **AUTOMATED BOUNDED CONTROL:** only for pre-approved low-risk control loops with certified limits, independent interlocks, watchdog and emergency stop.
- **SAFE STATE:** halt actuation and move to a defined safe condition where physically possible.

Mode transitions require explicit policy. A model cannot promote itself from OBSERVE to ACT.

## 3. Architecture

```text
SENSORS / DEVICE TELEMETRY
          |
          v
DEVICE IDENTITY + ATTESTATION
          |
          v
OBSERVATION VALIDATION + TIME / UNIT NORMALIZATION
          |
          v
DIGITAL TWIN / NEXUS SYSTEM MODEL
          |
          +------> MIRROR WORLD SCENARIO
          |                |
          |                v
          |         SIMULATION + SAFETY REVIEW
          |                |
          +----------------+
                           |
                           v
                   PROPOSED ACTION PLAN
                           |
                           v
              POLICY + RISK + CAPABILITY GATE
                           |
                  HUMAN APPROVAL (as required)
                           |
                           v
               INDEPENDENT SAFETY INTERLOCK
                           |
                           v
                 DEVICE / ACTUATOR ADAPTER
                           |
                           v
                POST-ACTION OBSERVATION
                           |
                           v
              RESULT VERIFICATION + AUDIT
```

## 4. Component responsibilities

### Device Registry and Identity
Tracks hardware identity, ownership, firmware, attestation, capability profile, location/scope where relevant, lifecycle and revocation state. A compromised or stale-attestation device is treated as untrusted.

### Sensor Ingestion
Validates source, units, calibration, timestamp, sequence, plausibility bounds and missing-data state. Sensor readings remain observations with quality metadata; they are not automatically ground truth.

### Twin State Manager
Maintains observed state, estimated state, predicted state and commanded state as separate values. It records synchronization lag, calibration, uncertainty and divergence.

### Safety Envelope Registry
Defines physical limits, prohibited states, permitted operating region, maximum rate of change, thermal/electrical/mechanical constraints, environmental constraints and required human supervision.

### Action Proposal Engine
Creates a typed proposed action with preconditions, expected effects, uncertainty, rollback/compensation plan, time limit and resource requirements. It has no direct device credentials.

### Human Approval Service
Provides review for high-impact, irreversible, hazardous, regulated or uncertain actions. Approval binds principal, device, exact action digest, context, time window and revocation conditions.

### Independent Safety Interlock
A separate control boundary checks hardware limits and emergency-stop state. It must remain effective if the AI planner, model provider or general runtime is compromised.

### Actuator Adapter
Executes only exact, authorized, bounded commands. It enforces idempotency, sequence, timeout, safe-state behavior and result acknowledgment.

### Post-Action Verifier
Compares commanded, acknowledged and observed states. Unexpected deviation stops further automation and raises an incident.

## 5. Physical safety invariants

- No actuator command without explicit device identity, scoped capability and policy decision.
- No high-risk actuation based solely on simulation output or model confidence.
- Independent hardware/software interlocks cannot be disabled by agents.
- Emergency stop and manual override take precedence.
- Loss of communications triggers a device-specific safe state, not an assumed retry.
- Sensor disagreement and stale telemetry reduce authority; they do not get averaged into false certainty.
- Every action is bounded in magnitude, duration, frequency and target.
- Recovery does not automatically replay a previously issued physical command.
- A rollback plan must account for irreversible physical effects; some actions are non-compensable.

## 6. Integration with MIRROR WORLD

MIRROR WORLD is the preferred place to explore alternatives before physical action. The simulation manifest must bind the twin revision, scenario, model versions, assumptions and uncertainty. Simulation can inform risk assessment but does not replace a safety case, physical testing or required certification.

Twin-to-device write-back is a distinct, high-risk capability with a separate contract, identity, approval and audit path.

## 7. Failure semantics

- Missing or invalid device identity: deny.
- Stale or implausible sensor state: downgrade to observe/recommend or safe state.
- Interlock fault: deny actuation and raise incident.
- Lost acknowledgment: do not blindly repeat; reconcile actual device state.
- Unexpected physical outcome: stop automation, preserve evidence and escalate.
- Network partition: device-specific safe behavior.
- Compromised edge node: revoke node, isolate device control path and require trusted recovery.

## 8. Architecture acceptance criteria

The architecture is not integration-ready until every device class has an explicit safety envelope, operating mode, sensor/actuator contract, identity and revocation behavior, human approval rule, independent interlock, communication-loss behavior, post-action verification, audit record and recovery procedure. This is a design specification only; no physical control is implemented or authorized by this document.
