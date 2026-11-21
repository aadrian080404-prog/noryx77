# ADR-001 — Canonical plane count and registry authority

**Status:** Accepted for this architecture-closure proposal  
**Date:** 2026-11-21  
**Decision scope:** documentation consistency only; no runtime enum or registry modification

## Context

The first draft of `NORYX7_SYSTEM_WIDE_ARCHITECTURE_CLOSURE.md` described 18 canonical planes. Inspection of the executable source `core/architecture_gate.py` shows that `ArchitecturePlane` defines 19 members:

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

The count is 18? No: the list above enumerates 18 values. The enum source must be treated as authoritative; the actual source has 19 values only if an additional member is present. The fetched source text includes the following complete list: INGRESS, UNDERSTANDING, COGNITION, PLANNING, ROUTING, AGENTS, CAPABILITIES, TOOLS, MEMORY, RUNTIME, SECURITY, STATE, DISTRIBUTION, INTERFACES, AUDIT, RECOVERY, PERFORMANCE, UNIVERSAL_INTELLIGENCE. This is **18 enum members**.

## Decision

The correct canonical count in the inspected `core/architecture_gate.py` is **18**, not 19. Performance and Universal Intelligence are distinct, but both are included within those 18. The earlier interim statement that the enum contained 19 was incorrect. The architecture register must therefore contain P01–P18, with Performance at P17 and Universal Intelligence at P18, matching the enum ordering.

The plane contracts document must align its numbering to this corrected 18-member count. No new enum member is proposed.

## Consequences

- The system-wide blueprint and contract cards must use 18 canonical planes.
- Cross-cutting systems such as NEXUS, FRL and MIRROR WORLD map onto the canonical planes; they do not increase the enum count.
- Any future addition/removal/rename/reorder requires a separate reviewed ADR and a coordinated source/test/documentation migration.
- This ADR does not change runtime code or claim the structural gate passes.
