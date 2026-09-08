# NORYX7 — Architecture Freeze Contract

## Status

This branch is the **architecture-freeze candidate**. The architecture is considered structurally closed only when the checks below remain true; runtime correctness is established separately by the global verification gate.

## Freeze invariants

1. The four fronts are explicitly declared: JARVIS, Browser, HYPERSYNTH, and Orchestration.
2. Every declared front has its required concrete paths.
3. No duplicated Python package tree is permitted under `core/core/`.
4. Public recovery APIs resolve to the authoritative epoch-aware `core.recovery.RecoveryController`.
5. Offline execution remains an explicit boundary and cannot silently fall back to cloud routing.
6. Browser v0.1 remains isolated from AI/HYPERSYNTH functionality and tracking/telemetry.
7. Models and agents remain untrusted proposals; policy, capabilities, verification, and state commit remain authoritative.
8. Architecture closure is fail-closed: structural omissions or forbidden paths block the gate.
9. Component verification covers `core`, `noryx7_runtime`, `ecosystem`, `tests`, JARVIS tests, and Browser tests.
10. No merge to `main` is authorized by this document alone; the global verification gate must provide the evidence.

## Separation of concerns

Architecture closure answers **"is every required structure present and unambiguous?"**.

Global verification answers **"does the frozen structure actually behave correctly under its contracts, adversarial cases, recovery transitions, offline execution, distributed routing, Browser isolation, and regression suites?"**.

These gates are intentionally separate so a green structural inventory cannot be mistaken for runtime proof.
