# NORYX7 — Confirmed PR File-Overlap and Integration Map

**Snapshot:** 2026-11-15  
**Source:** GitHub `pulls/{number}/files` for the listed open PRs.  
**Purpose:** identify concrete shared-file integration seams before merging stacked work.

This map reports filename overlap only. It does not establish that two changes conflict semantically; that requires patch and test review. It also does not imply that the listed PRs are ready to merge.

## Confirmed shared-file groups

| Shared path / seam | PRs touching it | Integration concern |
|---|---|---|
| `core/adversarial.py` | #12, #13, #22 | Preserve campaign semantics, seed reproducibility and workload bounds across extensions. |
| `core/scenario_matrix.py` | #12, #13, #22 | Single canonical scenario schema and compatible axis definitions. |
| `tests/million_scale_campaign.py` | #8, #12, #13, #22 | Avoid duplicate or contradictory campaign entry points and ensure deterministic resource budgets. |
| `tests/aggregate_campaign.py` | #12, #13, #22 | Keep aggregate reporting and stratification consistent. |
| `core/surf_contracts.py` | #8, #12 | Align SURF contract definitions with the security baseline. |
| `noryx7_runtime/contracts.py` | #8, #16, #18 | One versioned execution/authorization contract; do not let plan-binding and replay guards diverge. |
| `noryx7_runtime/engine.py` | #8, #16, #18, #23, #25 | Highest-risk runtime seam: plan digest, replay protection, durable state and authorization must compose in one canonical dispatch path. |
| `noryx7_runtime/test_engine_replay.py` | #8, #16, #18, #23 | Preserve all replay/plan-binding regressions in one cumulative test suite. |
| `noryx7_runtime/process_executor.py` | #27, #34, #36, #39 | Process isolation, deadline propagation, finite budget validation and process-tree termination must be integrated as one executor lifecycle. |
| `tests/test_process_executor.py` | #27, #34, #36, #39 | Merge tests cumulatively; validate kill, timeout, cancellation and descendant cleanup. |
| `core/distributed_memory.py` | #47, #55, #70 | Causal replication, contiguous counters and transitive vector-clock closure must share one acceptance algorithm. |
| `core/test_memory_counter_continuity.py` | #55, #70 | Counter and dependency-closure tests must remain mutually consistent. |
| `core/https_memory_peer.py` | #54, #67 | mTLS transport and certificate-to-agent binding/request bounds are one integrated trust boundary. |
| `core/test_https_memory_peer.py` | #54, #67 | Ensure transport, identity binding and resource limits are tested together. |
| `core/remote_witness.py` | #38, #63, #66 | Remote witness protocol, quorum semantics and durable audit anchoring need a single monotonic state contract. |
| `core/quorum_witness.py` | #63, #66 | Quorum policy and SQLite audit integration must not create divergent witness state. |
| `core/test_quorum_witness.py` | #63, #66 | Retain strict-majority, replay, rollback and persistence cases. |
| `core/sqlite_audit.py` | #57, #65 | Durable chain and external anti-rollback anchor must compose without duplicate sequence authority. |
| `core/hypersynth_runtime.py` | #62, #64, #68, #71 | Canonical runtime composition, sandbox capability and identity revalidation must use the same construction and dispatch boundary. |
| `core/operational_runtime.py` | #61, #68, #71 | Durable audit and sandbox/identity adapters must be injected through one composition root. |
| `core/runtime.py` | #61, #68, #71 | Ensure runtime entry points do not bypass authorization, audit or sandbox injection. |
| `core/os_sandbox.py` | #45, #62 | OS sandbox primitive and HYPERSYNTH capability adapter must retain fail-closed behavior. |
| `core/collaboration.py` | #64, #71 | Agent identity must be revalidated across every collaboration/inference turn and before action dispatch. |
| `core/identity.py` | #46, #64, #71 | Durable identity, collaboration revalidation and runtime sandbox identity must share epoch/revocation semantics. |
| `core/system_inspector.py` | #50, #72 | Static Python inspection and ELF descriptor integration need one bounded, non-executing analysis contract. |
| `core/test_elf_inspector.py` | #69, #72 | ELF parser tests and integrated system-inspector tests must be retained together. |

## Domain seams without confirmed filename overlap in this sample

- Matrix Core #73: broad, dedicated `core/matrix_*` implementation family. Review its resource grant, fencing, ledger, budget, scheduler, transfer and safety gate contracts against the device sovereignty invariants in the blueprint.
- SURF receipt #17: identity-bound verification receipts; integrate with the common evidence/audit contract.
- Agent dispatch #48: atomic identity-authorized dispatch; verify against the same revocation generation and execution intent used by runtime.
- Durable key lifecycle #29/#32/#43/#51: inspect branch ancestry and key-provider contracts together before consolidation.
- Identity persistence #26/#31/#46: reconcile duplicates/successors by ancestry and code equivalence, not by title alone.
- Durable state and journal line #14/#19/#24/#25/#38/#40/#41: maintain one authoritative journal/anchor lifecycle.

## Required merge discipline for each overlap group

1. Select the oldest valid parent branch in the declared ancestry.
2. Apply child commits in dependency order, preserving every unique test and migration.
3. Resolve conflicts by contract semantics, not by choosing one side wholesale.
4. Run focused tests on the cumulative branch after each integration step.
5. Run the relevant end-to-end, crash/replay, concurrency and adversarial tests on the final candidate.
6. Compare the candidate against the parent and confirm no unrelated changes were introduced.
7. Update the PR body with integrated commit SHA, test evidence and remaining limitations.
8. Do not merge to `main` until the full dependency chain and required checks are green and reviewed.

## Priority integration sequence

1. Runtime dispatch and authorization: #8 → #12 baseline, then #16/#18/#23/#24/#25 and the process-executor chain #27/#34/#36/#39.
2. Durable identity, keys and audit: #26/#29/#30/#31/#32/#33, then #38/#40/#41 and the newer #44/#56/#57/#61/#65/#66 line.
3. Memory: #28/#37, then #47/#52/#54/#55/#58/#59/#67/#70; reconcile #42 separately.
4. Sandbox and agent identity: #45/#53/#62/#68/#71 with #46/#48/#64.
5. SURF/System Inspector: #17/#50/#60/#69/#72.
6. Adversarial verification: #13/#22 after the runtime and memory contracts stabilize.
7. Matrix Core #73 integrates against the finalized identity, policy, budget, audit and node grant contracts.

The order is a proposed integration plan derived from current branch ancestry and overlap, not permission to merge automatically. All PRs remain subject to patch review and CI evidence.
