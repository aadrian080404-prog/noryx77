from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def replace_any(path: str, variants: list[tuple[str, str]], label: str) -> None:
    p = ROOT / path
    s = p.read_text()
    for old, new in variants:
        if old in s:
            p.write_text(s.replace(old, new, 1))
            print(f"PATCHED {label}")
            return
    if any(new in s for _, new in variants):
        print(f"ALREADY_PATCHED {label}")
        return
    raise RuntimeError(f"no compatible source pattern for {label}")

# Runtime: preserve legacy result shape and expose canonical verification evidence.
replace_any("core/runtime.py", [
    ('return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n                "result": final_answer, "verification": aggregate_verification,',
     'return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n                "result": final_answer, "results": results, "verification": aggregate_verification,'),
], "runtime_completed_results")
replace_any("core/runtime.py", [
    ('principal_id, principal_key_fingerprint = self._principal_binding("deterministic")\n        payload = self._offline_payload(task)',
     ('_, principal_key_fingerprint = self._principal_binding("deterministic")\n        principal_id = getattr(task, "principal_id", None) or execution_id\n        payload = self._offline_payload(task)'),
], "offline_identity_binding")
replace_any("core/runtime.py", [
    ('self.audit.record("orchestration_context", task_id=task_id, context_id=interaction_context.context_id,',
     'self.audit.record("orchestration_context", task_id=task_id, context_id=envelope.interaction_context.context_id,'),
], "runtime_context_audit")

# Rejections caused by forged agent/task identity must carry canonical verification evidence.
replace_any("core/runtime.py", [
    ('return self._rejection(envelope, child.task_id, "agent_identity_mismatch", self.audit)',
     'return self._rejection(envelope, child.task_id, "agent_identity_mismatch", self.audit, verification=VerificationResult(False, "agent_result", "agent_identity_mismatch"))'),
], "agent_identity_verification")
replace_any("core/runtime.py", [
    ('return self._rejection(envelope, child.task_id, "task_identity_mismatch", self.audit)',
     'return self._rejection(envelope, child.task_id, "task_identity_mismatch", self.audit, verification=VerificationResult(False, "agent_result", "task_identity_mismatch"))'),
], "task_identity_verification")

# SecureChannel: the repository's compatibility contract is strict monotonic receive ordering.
replace_any("core/secure_channel.py", [
    ('MAX_SEQUENCE: Final[int] = (1 << 64) - 1\nREPLAY_WINDOW: Final[int] = 4096',
     'MAX_SEQUENCE: Final[int] = (1 << 64) - 1'),
], "secure_channel_window_constant")
replace_any("core/secure_channel.py", [
    ('        self._send_sequence, self._last_received = 0, -1\n        self._received_sequences: set[int] = set()\n        self._send_lock',
     '        self._send_sequence, self._last_received = 0, -1\n        self._send_lock'),
], "secure_channel_receive_state")
replace_any("core/secure_channel.py", [
    ('            if frame.sequence in self._received_sequences:\n                raise ValueError("replayed_frame")\n            if self._last_received >= 0 and frame.sequence + REPLAY_WINDOW <= self._last_received:\n                raise ValueError("replayed_frame")',
     '            if frame.sequence <= self._last_received:\n                raise ValueError("replayed_frame")'),
], "secure_channel_monotonic_guard")
replace_any("core/secure_channel.py", [
    ('            self._received_sequences.add(frame.sequence)\n            if frame.sequence > self._last_received:\n                self._last_received = frame.sequence\n            floor = self._last_received - REPLAY_WINDOW + 1\n            if floor > 0:\n                self._received_sequences.intersection_update(\n                    sequence for sequence in self._received_sequences if sequence >= floor\n                )',
     '            self._last_received = frame.sequence'),
], "secure_channel_monotonic_commit")

print("ZERO_FAILURE_COMPAT_REPAIRS_APPLIED")
