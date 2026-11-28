# ADR-001 — Canonical plane count and registry authority

**Status:** Accepted for this architecture-closure proposal  
**Date:** 2026-11-21  
**Decision scope:** documentation consistency only; no runtime enum or registry modification

## Context

An interim review message incorrectly stated that `core/architecture_gate.py` contained 19 canonical planes. Direct inspection of the complete `ArchitecturePlane` enum shows exactly **18 members**:

1. ingress
2. understanding
3. cognition
4. planning
5. routing
6. agents
7. capabilities
8. tools
9. memory
10. runtime
11. security
12. state
13. distribution
14. interfaces
15. audit
16. recovery
17. performance
18. universal_intelligence

`core/architecture_registry.py` provides definitions for these enum members. Performance and Universal Intelligence are distinct planes, but their inclusion does not create a nineteenth plane.

## Decision

The canonical count is **18**, with P01–P18 matching the enum order. The first system-wide blueprint already used an 18-row inventory; the subsequent draft edits introduced an accidental duplicate Performance row and a spurious P19. Those documentation errors are corrected by this ADR and the aligned system blueprint.

No runtime enum, registry, test or frozen baseline is changed. Cross-cutting domains such as NEXUS, FRL, MIRROR WORLD, Knowledge, Privacy and Human Control map onto the 18 canonical planes; they do not increase the enum count.

## Consequences

- All architecture indexes and contract packs use 18 canonical planes.
- Performance is P17; Universal Intelligence is P18.
- Future addition, removal, rename or reorder requires a separate reviewed ADR and coordinated source/test/documentation migration.
- This ADR does not claim that the architecture gate passes or that all plane implementations are complete.
