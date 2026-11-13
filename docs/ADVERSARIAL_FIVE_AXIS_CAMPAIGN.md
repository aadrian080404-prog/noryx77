# NORYX7 Adversarial Campaign — Five-Axis Matrix

Status: implementation candidate in PR #22; CI pending.

## Coverage dimensions

The deterministic synthetic campaign now assigns every scenario a coordinate across five independent dimensions:

| Dimension | Values |
|---|---:|
| Entity class | 9 |
| Power tier | 7 |
| Capability class | 8 |
| Behavior class | 8 |
| Impact class | 6 |
| **Total strata** | **24,192** |

Entity classes describe who or what is acting. Power tiers describe the resources and privilege level. Capability classes describe what the entity can do. Behavior classes describe how it operates. Impact classes describe the affected security or operational property.

Each case ID and seed maps to exactly one stable five-axis coordinate. The full 10,000,000-case matrix is deterministically balanced: every stratum receives either floor(10,000,000 / 24,192) or ceiling(10,000,000 / 24,192) cases. The expected count is generated independently from the observed shard counts and checked during aggregation.

## Sharding and aggregation

- Each shard reports counts for all five individual axes, the legacy entity × power matrix and the complete five-axis matrix.
- The aggregator checks the exact shard index set, per-shard execution budget, configuration, evidence scope, schema, totals and every full-matrix cell.
- Shard counts do not need to be coprime with the total number of strata. All shard index ranges are disjoint and their union covers the requested global case IDs.
- Difficulty quotas are enforced on complete campaigns, not incorrectly imposed on each partial shard.
- PR CI remains bounded to 10,000 synthetic cases. The full 10-million campaign is configurable but has not been claimed as executed.

## What the evidence means

The campaign verifies deterministic scenario generation, coordinate allocation, structural preflight and synthetic invariants. It does not execute 10 million live attacks, prove runtime containment, or measure true false-positive/false-negative rates. Those require instrumented target systems, independently labelled ground truth, real execution receipts and separate evaluation of detection and recovery.

The campaign therefore reports volume and synthetic coverage separately from implementation/runtime proof.
