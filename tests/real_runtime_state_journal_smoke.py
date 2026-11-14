from __future__ import annotations

import hashlib
import time

from noryx7_runtime.attestation import (
    Ed25519AttestationSigner,
    Ed25519AttestationVerifier,
    attestation_digest,
)
from noryx7_runtime.contracts import ExecutionStatus, Intent, PlanStep
from noryx7_runtime.engine import RuntimeEngine
from noryx7_runtime.state import StateJournal


def main() -> None:
    print("=" * 72)
    print("NORYX7 — REAL RUNTIME + STATE JOURNAL SMOKE")
    print("=" * 72)

    signer = Ed25519AttestationSigner.generate()
    verifier = Ed25519AttestationVerifier.from_public_key_bytes(
        signer.public_key_bytes
    )

    journal = StateJournal(
        verifier=verifier,
        runtime_id="runtime-state-smoke",
    )

    engine = RuntimeEngine(
        runtime_id="runtime-state-smoke",
        state_journal=journal,
        attestation_signer=signer,
        max_actions=8,
    )

    dispatch = []
    verified = []
    committed = []

    def executor(action):
        dispatch.append(action.step_id)
        print(f"DISPATCH {len(dispatch)} {action.step_id}")
        return {
            "ok": True,
            "step_id": action.step_id,
        }

    def verify(action, output):
        valid = (
            isinstance(output, dict)
            and output.get("ok") is True
            and output.get("step_id") == action.step_id
        )
        verified.append((action.step_id, valid))
        print(f"VERIFY {action.step_id} {'PASS' if valid else 'FAIL'}")
        return valid

    def commit(action, attestation, output):
        committed.append(
            (
                action.step_id,
                attestation.verified,
                attestation.runtime_id,
            )
        )
        print(
            f"COMMIT {action.step_id} "
            f"verified={attestation.verified} "
            f"runtime={attestation.runtime_id}"
        )

    intent = Intent(
        text="state journal runtime smoke",
        principal_id="state-smoke-principal",
        intent_id="state-smoke-intent-001",
    )

    steps = (
        PlanStep(
            step_id="step-001",
            action_type="deterministic_test",
            target="state-journal-smoke",
            parameters={"index": 1},
        ),
        PlanStep(
            step_id="step-002",
            action_type="deterministic_test",
            target="state-journal-smoke",
            parameters={"index": 2},
            dependencies=("step-001",),
        ),
    )

    started = time.perf_counter()

    result = engine.execute(
        intent,
        steps,
        executor=executor,
        verifier=verify,
        committer=commit,
        timeout_seconds=30.0,
        execution_id="state-smoke-execution-001",
    )

    elapsed = time.perf_counter() - started

    entries = journal.snapshot()

    print()
    print(f"RESULT_TYPE = {type(result).__name__}")
    print(f"STATUS = {result.status}")
    print(f"EXECUTION_ID = {result.execution_id}")
    print(f"ERROR = {result.error}")
    print(f"OUTPUTS = {len(result.outputs)}")
    print(f"ATTESTATIONS = {len(result.attestations)}")
    print(f"JOURNAL_ENTRIES = {len(entries)}")
    print(f"DISPATCH_COUNT = {len(dispatch)}")
    print(f"VERIFY_COUNT = {len(verified)}")
    print(f"COMMIT_COUNT = {len(committed)}")
    print(f"ELAPSED_SECONDS = {elapsed:.6f}")

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.error is None
    assert len(result.outputs) == 2
    assert len(result.attestations) == 2

    assert dispatch == ["step-001", "step-002"]
    assert [step_id for step_id, ok in verified] == [
        "step-001",
        "step-002",
    ]
    assert all(ok for _, ok in verified)

    assert [step_id for step_id, _, _ in committed] == [
        "step-001",
        "step-002",
    ]
    assert all(verified_flag for _, verified_flag, _ in committed)
    assert all(runtime_id == "runtime-state-smoke"
               for _, _, runtime_id in committed)

    assert len(entries) == 2

    assert all(entry.runtime_id == "runtime-state-smoke" for entry in entries)
    assert all(entry.execution_id == result.execution_id for entry in entries)
    assert all(entry.principal_id == intent.principal_id for entry in entries)

    # The second attestation must continue the first attestation's chain.
    first_digest = attestation_digest(result.attestations[0])
    assert result.attestations[1].previous_attestation_digest == first_digest

    # Journal reconstruction must preserve the same chain.
    assert entries[1].previous_attestation_digest == first_digest

    # Action/output provenance must be represented in every committed entry.
    assert all(len(entry.action_digest) == 64 for entry in entries)
    assert all(len(entry.output_digest) == 64 for entry in entries)

    print()
    print("RUNTIME = PASS")
    print("STATE_JOURNAL = PASS")
    print("RESERVATION_COMMIT_PATH = PASS")
    print("ATTESTATION_CHAIN = PASS")
    print("PROVENANCE_DIGESTS = PASS")
    print("=" * 72)
    print("REAL RUNTIME + STATE JOURNAL SMOKE PASSED")
    print("=" * 72)


if __name__ == "__main__":
    main()
