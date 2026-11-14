# Global verification matrix

## Identity
- principal swapping
- agent key substitution
- runtime swapping
- execution swapping
- revoked/replaced identities

## Cryptography
- payload tampering
- authenticated metadata tampering
- wrong key
- signature forgery
- nonce/sequence exhaustion
- directional reflection
- replay
- chain truncation/reordering

## Runtime
- invalid lifecycle transitions
- action budget exhaustion
- deadline expiry before dispatch
- cyclic/missing dependencies
- malformed adapter results
- verifier exceptions
- commit failures

## Memory
- cross-execution reads
- cross-execution writes
- cross-execution deletes
- same logical memory ID in separate executions
- mutable-object aliasing
- capacity exhaustion

## Model Fabric / HYPERSYNTH
- request/result mismatch
- candidate metadata tampering
- selected-model substitution
- output digest mismatch
- confidence type confusion
- NaN/Infinity
- synthesizer failure
- cross-execution replay
- provenance seal mismatch

## Multi-agent
- replayed evidence
- pair retargeting
- revision rollback
- same-agent consensus
- disagreement without valid challenge
- revoked identity

Passing all current tests establishes only the implemented invariants. Security review remains iterative and must be repeated after every contract or trust-boundary change.
