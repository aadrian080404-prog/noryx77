from pathlib import Path


def patch(path: str, replacements: list[tuple[str, str]], label: str) -> None:
    p = Path(path)
    s = p.read_text()
    for old, new in replacements:
        if new in s:
            continue
        if old in s:
            s = s.replace(old, new, 1)
            p.write_text(s)
            print(f"PATCHED {label}")
            return
    print(f"ALREADY_PATCHED {label}")


# Runtime contract compatibility: completed results must expose the result list,
# and identity-tamper rejections must expose a structured verification verdict.
patch(
    "core/runtime.py",
    [
        (
            'return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n'
            '                "result": final_answer, "verification": aggregate_verification,',
            'return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n'
            '                "result": final_answer, "results": results, "verification": aggregate_verification,',
        ),
        (
            'result = {"status": "rejected", "reason": reason, "task_id": task_id}\n        result.update(extra)',
            'result = {"status": "rejected", "reason": reason, "task_id": task_id}\n'
            '        if "verification" not in extra and reason in {"agent_identity_mismatch", "task_identity_mismatch"}:\n'
            '            extra["verification"] = VerificationResult(False, "agent_result", reason)\n'
            '        result.update(extra)',
        ),
    ],
    "runtime_contract_surface",
)

# Offline execution must reject non-verifiable result types before the generic
# verifier's permissive presence check can admit them. This keeps the offline
# commit boundary fail-closed without changing verification semantics globally.
patch(
    "core/runtime.py",
    [
        (
            '        def commit(execution_record, result):\n            verification = self.verifier.verify_output(result, stage="runtime_result")',
            '        def commit(execution_record, result):\n'
            '            if not isinstance(result, (str, bytes)):\n'
            '                raise PermissionError("offline_result_unverified")\n'
            '            verification = self.verifier.verify_output(result, stage="runtime_result")',
        ),
    ],
    "offline_result_type_gate",
)

# Repository contract requires strict monotonic receive ordering. Restore it if
# a local compatibility script installed the broader bounded replay window.
patch(
    "core/secure_channel.py",
    [
        (
            '            if frame.sequence in self._received_sequences:\n'
            '                raise ValueError("replayed_frame")\n'
            '            if self._last_received >= 0 and frame.sequence + REPLAY_WINDOW <= self._last_received:\n'
            '                raise ValueError("replayed_frame")',
            '            if frame.sequence <= self._last_received:\n'
            '                raise ValueError("replayed_frame")',
        ),
        (
            '            self._received_sequences.add(frame.sequence)\n'
            '            if frame.sequence > self._last_received:\n'
            '                self._last_received = frame.sequence\n'
            '            floor = self._last_received - REPLAY_WINDOW + 1\n'
            '            if floor > 0:\n'
            '                self._received_sequences.intersection_update(\n'
            '                    sequence for sequence in self._received_sequences if sequence >= floor\n'
            '                )',
            '            self._last_received = frame.sequence',
        ),
    ],
    "secure_channel_strict_replay",
)

print("ZERO_FAILURE_COMPAT_V2_APPLIED")
