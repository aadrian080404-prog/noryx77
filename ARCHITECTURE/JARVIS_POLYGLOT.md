# NORYX7 JARVIS Polyglot Runtime

The JARVIS subsystem is intentionally polyglot. Python owns model/agent orchestration and evaluation; Rust owns security-sensitive runtime primitives and deterministic execution helpers; Go owns long-lived network gateway services; Kotlin/Android owns device/audio integration; TypeScript owns rich UI surfaces.

## Boundary rule
No language bypasses NORYX7 authorization. Every external capability enters through the canonical ToolExecutor/ActionGate path. Wake detection creates a session only; it never grants an execution capability.

## Runtime flow
INPUT -> PERCEPTION -> CONTEXT -> AGENT -> PLAN/VERIFY -> AUTHORIZATION -> EXECUTION FABRIC -> OBSERVATION -> RESULT VERIFY -> AUDIT/MEMORY.

## Current implemented contracts
- deterministic double-clap wake detector
- explicit JARVIS session state machine
- provider-neutral voice boundary
- authorized context acquisition
- authorized observation fabric
- canonical multimodal core already present
- canonical tool/execution/authorization fabric already present
- Rust execution/digest boundary
- Go gateway boundary

## Device integration
The contracts are provider-neutral. A real Android microphone client must explicitly request microphone permission and feed PCM/audio events into the wake boundary. No repository contract treats wake detection as device authorization.

## Security invariants
1. deny by default
2. wake != authorization
3. observation requires source authorization
4. tools require capability authorization and provenance
5. execution remains auditable and verifiable
6. payloads can remain outside durable state by digest/reference
