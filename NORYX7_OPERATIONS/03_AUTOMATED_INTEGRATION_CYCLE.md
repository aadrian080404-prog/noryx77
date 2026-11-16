# NORYX7 — Automated Architecture Integration Cycle

## Objective

Run one repeatable integration cycle from the repository state: inventory the architecture, validate its dependency graph, compile source, run the complete Python test suite, build/test the Android browser, and publish evidence. The cycle is repeatable on every pull request; it is not a claim that all planned NORYX7 capabilities are implemented.

## One-cycle command sequence

From the repository root:

```bash
python scripts/validate_integration_manifest.py
python -m compileall -q core noryx7_runtime ecosystem jarvis web
python -m pytest core noryx7_runtime ecosystem jarvis tests -q
cd noryx-browser
gradle test assembleDebug --no-daemon
```

The GitHub Actions workflows run these checks automatically. The graph validator is intentionally dependency-free and uses only the Python standard library.

## Machine-readable source of truth

- `architecture/noryx7_integration_manifest.json`: module IDs, architecture planes, evidence status, source paths, dependencies, test targets, and candidate PR references.
- `scripts/validate_integration_manifest.py`: validates schema, unique IDs, legal status, source paths, dependency references, path traversal, and dependency cycles.
- `tests/test_integration_manifest.py`: regression tests for valid graphs and malformed/missing/cyclic inputs.

## Evidence states

- `implemented_partial`: code exists, but one or more integration, security, durability, scale, or production gates remain open.
- `implemented`: code and its declared local contract tests exist. This does not automatically mean production-ready.
- `candidate_only`: code exists on a separate unmerged PR and must not be imported as though it were on this branch.
- `specification_only`: architecture is documented, but a complete implementation is not present on this branch.

The validator checks structure and source presence only. It cannot promote a module to `integrated` or `operational_verified`.

## Integration rules

1. Keep each feature isolated until its contracts and tests pass.
2. Integrate in dependency order, not by PR number or convenience.
3. Before combining branches, compare changed-file lists and reconcile overlaps explicitly.
4. Re-run the full cycle on the exact resulting commit SHA.
5. Keep candidate-only modules out of production imports until their PR is reviewed and merged.
6. A fake provider, simulated peer, or local in-memory adapter proves only the tested boundary.
7. Preserve fail-closed behavior: missing identity, authorization, key material, durable state, or remote trust evidence must not be silently substituted.

## Completion gates after this automation

The automated cycle is the fast structural and regression loop. The following require dedicated evidence beyond ordinary CI:

- real device enrollment and authenticated device-to-device transport;
- persistent key custody and revocation across restart;
- distributed memory consistency under partitions and replay;
- remote executor generation fencing and proof of stop;
- durable offline outbox recovery;
- SURF evidence capture, reproducibility, and sandbox isolation;
- real provider/network smoke tests and production telemetry;
- operational load, endurance, disaster-recovery, and independent security review.

No deployment, merge to `main`, or change to the frozen architecture branch is authorized by this automation.
