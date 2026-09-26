from __future__ import annotations

import inspect
import time

from noryx7_runtime.contracts import Intent, PlanStep
from noryx7_runtime.engine import RuntimeEngine


def main() -> None:
    print("=" * 72)
    print("NORYX7 — REAL RUNTIME EXECUTION SMOKE")
    print("=" * 72)

    print("RUNTIME_CLASS =", RuntimeEngine.__module__ + "." + RuntimeEngine.__name__)

    dispatch_count = 0
    verify_count = 0
    commit_count = 0

    def executor(envelope):
        nonlocal dispatch_count
        dispatch_count += 1
        print(
            "DISPATCH",
            dispatch_count,
            envelope.step_id,
            envelope.action_type,
            envelope.target,
        )
        return {
            "ok": True,
            "step_id": envelope.step_id,
            "target": envelope.target,
        }

    def verifier(envelope, output):
        nonlocal verify_count
        verify_count += 1
        valid = (
            isinstance(output, dict)
            and output.get("ok") is True
            and output.get("step_id") == envelope.step_id
        )
        print("VERIFY", verify_count, "PASS" if valid else "FAIL")
        return valid

    def committer(envelope, attestation, output):
        nonlocal commit_count
        commit_count += 1
        print(
            "COMMIT",
            commit_count,
            envelope.step_id,
            "verified=" + str(attestation.verified),
        )

    engine = RuntimeEngine(max_actions=8)

    print("ENGINE_INSTANCE =", type(engine).__name__)
    print("ENGINE_BUILD = PASS")

    signature = inspect.signature(engine.execute)
    print("EXECUTE_SIGNATURE =", signature)

    if len(signature.parameters) != 8:
        raise AssertionError(
            f"unexpected_execute_contract:{signature}"
        )

    print("ENGINE_API = PASS")

    intent = Intent(
        text="real runtime smoke execution",
        principal_id="smoke-principal",
        intent_id="real-runtime-smoke-001",
    )

    steps = (
        PlanStep(
            step_id="step-001",
            action_type="deterministic_test",
            target="runtime-smoke",
            parameters={"index": 1},
        ),
        PlanStep(
            step_id="step-002",
            action_type="deterministic_test",
            target="runtime-smoke",
            parameters={"index": 2},
            dependencies=("step-001",),
        ),
    )

    started = time.perf_counter()

    result = engine.execute(
        intent,
        steps,
        executor=executor,
        verifier=verifier,
        committer=committer,
        timeout_seconds=30.0,
        execution_id="real-runtime-smoke-execution-001",
    )

    elapsed = time.perf_counter() - started

    print()
    print("RESULT_TYPE =", type(result).__name__)
    print("STATUS =", result.status)
    print("EXECUTION_ID =", result.execution_id)
    print("ATTESTATIONS =", len(result.attestations))
    print("OUTPUTS =", len(result.outputs))
    print("ERROR =", result.error)
    print("DISPATCH_COUNT =", dispatch_count)
    print("VERIFY_COUNT =", verify_count)
    print("COMMIT_COUNT =", commit_count)
    print(f"ELAPSED_SECONDS = {elapsed:.6f}")

    if result.status.value != "succeeded":
        raise AssertionError(f"runtime_execution_failed:{result}")

    if dispatch_count != len(steps):
        raise AssertionError(
            f"dispatch_count_mismatch:{dispatch_count}!={len(steps)}"
        )

    if verify_count != len(steps):
        raise AssertionError(
            f"verify_count_mismatch:{verify_count}!={len(steps)}"
        )

    if commit_count != len(steps):
        raise AssertionError(
            f"commit_count_mismatch:{commit_count}!={len(steps)}"
        )

    if len(result.attestations) != len(steps):
        raise AssertionError(
            f"attestation_count_mismatch:{len(result.attestations)}!={len(steps)}"
        )

    if len(result.outputs) != len(steps):
        raise AssertionError(
            f"output_count_mismatch:{len(result.outputs)}!={len(steps)}"
        )

    print()
    print("REAL_RUNTIME_EXECUTE = PASS")
    print("SCHEDULING = PASS")
    print("DISPATCH = PASS")
    print("VERIFICATION = PASS")
    print("ATTESTATION = PASS")
    print("COMMIT = PASS")
    print("=" * 72)
    print("REAL RUNTIME SMOKE PASSED")
    print("=" * 72)


if __name__ == "__main__":
    main()
