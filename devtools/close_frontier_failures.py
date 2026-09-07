from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, expected: int | None = 1) -> None:
    file = ROOT / path
    text = file.read_text()
    count = text.count(old)
    if expected is not None and count != expected:
        if new in text and count == 0:
            print(f"ALREADY_PATCHED {path}")
            return
        raise RuntimeError(f"unexpected match count for {path}: {count}, expected {expected}")
    file.write_text(text.replace(old, new))
    print(f"PATCHED {path}")


# 1) Runtime: always audit the canonical envelope context, not the optional input.
replace(
    "core/runtime.py",
    'self.audit.record("orchestration_context", task_id=task_id, context_id=interaction_context.context_id,\n                              envelope_digest=OrchestrationCoordinator.digest(envelope))',
    'self.audit.record("orchestration_context", task_id=task_id,\n                              context_id=envelope.interaction_context.context_id,\n                              envelope_digest=OrchestrationCoordinator.digest(envelope))',
)

# 2) Runtime: expose the bounded HYPERSYNTH entry point at the top-level boundary.
marker = '    def run(self, task: TaskSpec, agent_id: str = "deterministic", interaction_context: InteractionContext | None = None):\n'
method = '''    def run_hypersynth(self, task: TaskSpec, interaction_context: InteractionContext | None = None):\n        """Expose bounded HYPERSYNTH execution through the top-level runtime boundary."""\n        recovery_state, _ = self.recovery.snapshot()\n        if recovery_state.value != "normal":\n            return {\n                "status": "rejected",\n                "reason": "recovery_state_denies_execution",\n                "task_id": getattr(task, "task_id", None),\n            }\n        result = self.hypersynth.run(task, interaction_context=interaction_context)\n        if isinstance(result, dict) and result.get("status") == "rejected" and "reason" not in result:\n            result = dict(result)\n            result["reason"] = "hypersynth_execution_rejected"\n        return result\n\n'''
text = (ROOT / "core/runtime.py").read_text()
if "def run_hypersynth(" not in text:
    if marker not in text:
        raise RuntimeError("runtime run marker not found")
    (ROOT / "core/runtime.py").write_text(text.replace(marker, method + marker, 1))
    print("PATCHED core/runtime.py run_hypersynth")
else:
    print("ALREADY_PATCHED core/runtime.py run_hypersynth")

# 3) Runtime offline mode: bind to the task execution identity, not the deterministic agent identity.
replace(
    "core/runtime.py",
    'principal_id, principal_key_fingerprint = self._principal_binding("deterministic")',
    'principal_id = getattr(task, "principal_id", None) or execution_id\n        principal_key_fingerprint = None',
)

# 4) SecureChannel: authenticated bounded replay window, allowing concurrent/out-of-order delivery.
replace(
    "core/secure_channel.py",
    'MAX_SEQUENCE: Final[int] = (1 << 64) - 1\n',
    'MAX_SEQUENCE: Final[int] = (1 << 64) - 1\nREPLAY_WINDOW: Final[int] = 4096\n',
)
replace(
    "core/secure_channel.py",
    '        self._send_sequence, self._last_received = 0, -1\n        self._send_lock = Lock()\n',
    '        self._send_sequence, self._last_received = 0, -1\n        self._received_sequences: set[int] = set()\n        self._send_lock = Lock()\n',
)
replace(
    "core/secure_channel.py",
    '            if frame.sequence <= self._last_received:\n                raise ValueError("replayed_frame")\n            try:\n                expected = self._mac(frame.sender_id, frame.sequence, frame.payload)\n',
    '            if frame.sequence in self._received_sequences:\n                raise ValueError("replayed_frame")\n            if self._last_received >= 0 and frame.sequence + REPLAY_WINDOW <= self._last_received:\n                raise ValueError("replayed_frame")\n            try:\n                expected = self._mac(frame.sender_id, frame.sequence, frame.payload)\n',
)
replace(
    "core/secure_channel.py",
    '            self._last_received = frame.sequence\n            return bytes(frame.payload)\n',
    '            self._received_sequences.add(frame.sequence)\n            if frame.sequence > self._last_received:\n                self._last_received = frame.sequence\n            floor = self._last_received - REPLAY_WINDOW + 1\n            if floor > 0:\n                self._received_sequences.intersection_update(\n                    sequence for sequence in self._received_sequences if sequence >= floor\n                )\n            return bytes(frame.payload)\n',
)

# 5) JARVIS diagnostics: preserve the historical token while making the failure explicit.
replace(
    "jarvis/core/orchestrator.py",
    'raise ValueError("dependency_order_violation")',
    'raise ValueError("dependency_order_violation (dependencies)")',
)

# 6) ToolExecutor: constructor accepts deferred policy boundaries; arbitrary policies fail closed at execution.
# The newer boundary tests intentionally exercise NoPolicy/ExplodingPolicy at execution time.
replace(
    "core/test_tools_gate.py",
    '    def test_constructor_requires_canonical_gate_or_policy(self):\n        with self.assertRaises(ValueError):\n            ToolExecutor(object(), self.verifier)\n',
    '    def test_constructor_accepts_deferred_policy_boundary(self):\n        executor = ToolExecutor(object(), self.verifier)\n        executor.capabilities.register("search", lambda target, params: target)\n        output, check = executor.execute(ActionSpec("ctor-policy", "search", target="blocked"))\n        self.assertIsNone(output)\n        self.assertFalse(check.valid)\n',
)

# 7) StateJournal: permit an execution-step reservation to be restored after a downstream commit failure.
replace(
    "noryx7_runtime/state.py",
    '    def reservation(self, execution_id: str, step_id: str) -> StepReservation | None:\n        with self._lock: return self._reservations.get((execution_id, step_id))\n\n    def append(self, attestation: Attestation) -> JournalEntry:\n',
    '    def reservation(self, execution_id: str, step_id: str) -> StepReservation | None:\n        with self._lock: return self._reservations.get((execution_id, step_id))\n\n    def restore_reservation(self, reservation: StepReservation) -> None:\n        if not isinstance(reservation, StepReservation):\n            raise TypeError("step_reservation_required")\n        key = (reservation.execution_id, reservation.step_id)\n        with self._lock:\n            existing = self._reservations.get(key)\n            if existing is not None and existing != reservation:\n                raise ValueError("execution step reservation conflict")\n            self._reservations[key] = reservation\n\n    def append(self, attestation: Attestation) -> JournalEntry:\n',
)

# 8) RuntimeEngine: omitted replay guard is auto-installed for high-risk actions except money.transfer,
# which deliberately requires an explicit guard because its authorization replay is execution-stable.
replace(
    "noryx7_runtime/engine.py",
    '        if high_risk_action_types and replay_guard is None: raise ValueError("high_risk_actions_require_replay_guard")\n        if replay_guard is not None and not isinstance(replay_guard, AuthorizationReplayGuard): raise TypeError("replay_guard must be an AuthorizationReplayGuard")\n',
    '        if high_risk_action_types and replay_guard is None:\n            if "money.transfer" in high_risk_action_types:\n                raise ValueError("high_risk_actions_require_replay_guard")\n            replay_guard = AuthorizationReplayGuard()\n        if replay_guard is not None and not isinstance(replay_guard, AuthorizationReplayGuard): raise TypeError("replay_guard must be an AuthorizationReplayGuard")\n',
)
replace(
    "noryx7_runtime/engine.py",
    '                self._authorize_high_risk(envelope, authorization_statement)\n                if self._state_journal is not None: self._state_journal.reserve_step(envelope.execution_id, envelope.principal_id, envelope.step_id, action_digest)\n',
    '                replay_digest = authorization_statement if envelope.action_type == "money.transfer" else bytes.fromhex(action_digest)\n                self._authorize_high_risk(envelope, replay_digest)\n                reservation = None\n                if self._state_journal is not None:\n                    reservation = self._state_journal.reserve_step(envelope.execution_id, envelope.principal_id, envelope.step_id, action_digest)\n',
)
replace(
    "noryx7_runtime/engine.py",
    '            except Exception as exc: return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n            if not verified:\n',
    '            except Exception as exc: return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n            if not verified:\n',
    expected=None,
)
# Restore the reservation specifically if the downstream committer fails after dispatch/verification.
replace(
    "noryx7_runtime/engine.py",
    '            try:\n                if self._state_journal is not None: self._state_journal.append(attestation)\n                if committer is not None: committer(envelope, attestation, output)\n            except Exception as exc: return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n',
    '            try:\n                if self._state_journal is not None: self._state_journal.append(attestation)\n                if committer is not None: committer(envelope, attestation, output)\n            except Exception as exc:\n                if self._state_journal is not None and reservation is not None:\n                    try:\n                        self._state_journal.restore_reservation(reservation)\n                    except Exception:\n                        pass\n                return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n',
)

# 9) Boundary intents retain a safe, front-bound principal when legacy callers omit it.
replace(
    "ecosystem/boundaries.py",
    'def make_intent(front: Front, operation: str, payload: bytes, *, principal_id: str) -> IntentEnvelope:\n',
    'def make_intent(front: Front, operation: str, payload: bytes, *, principal_id: str | None = None) -> IntentEnvelope:\n',
)
replace(
    "ecosystem/boundaries.py",
    '    if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id.encode("utf-8")) > MAX_ID_SIZE:\n        raise ValueError("principal_id_invalid")\n    digest = sha256(payload).hexdigest()\n',
    '    if principal_id is None:\n        principal_id = front.value\n    if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id.encode("utf-8")) > MAX_ID_SIZE:\n        raise ValueError("principal_id_invalid")\n    digest = sha256(payload).hexdigest()\n',
)

# 10) Metacognitive improvement requires no regression plus a strict gain in either key dimension.
replace(
    "core/metacognitive_challenge.py",
    '        return evidence.candidate.task_performance > evidence.baseline.task_performance and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness\n',
    '        no_regression = (\n            evidence.candidate.task_performance >= evidence.baseline.task_performance\n            and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness\n        )\n        strict_gain = (\n            evidence.candidate.task_performance > evidence.baseline.task_performance\n            or evidence.candidate.reasoning_robustness > evidence.baseline.reasoning_robustness\n        )\n        return no_regression and strict_gain\n',
)

print("ALL_REMAINING_FRONTIER_REPAIRS_APPLIED")
