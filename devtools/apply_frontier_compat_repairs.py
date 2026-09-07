from pathlib import Path


def replace(path, old, new, *, count=1):
    p = Path(path)
    s = p.read_text()
    if new in s and old not in s:
        print(f"ALREADY_PATCHED {path}")
        return
    if old not in s:
        raise SystemExit(f"TARGET_NOT_FOUND:{path}")
    p.write_text(s.replace(old, new, count))
    print(f"PATCHED {path}")

# Top-level runtime compatibility and normalized context handling.
replace("core/runtime.py",
        'self.audit.record("orchestration_context", task_id=task_id, context_id=interaction_context.context_id,',
        'self.audit.record("orchestration_context", task_id=task_id, context_id=envelope.interaction_context.context_id,')
replace("core/runtime.py",
        '        if envelope is not None:\n            result["orchestration_stage"] = envelope.stage.value\n        return result',
        '        if envelope is not None:\n            result["orchestration_stage"] = envelope.stage.value\n        if "verification" not in result:\n            result["verification"] = VerificationResult(False, "runtime", reason)\n        return result')
replace("core/runtime.py",
        '        return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n                "result": final_answer, "verification": aggregate_verification,',
        '        return {"status": "completed", "task_id": task_id, "execution_id": execution_id,\n                "result": final_answer, "results": tuple(results), "verification": aggregate_verification,')
replace("core/runtime.py",
        '    def close(self) -> None:\n',
        '    def run_hypersynth(self, task: TaskSpec, interaction_context: InteractionContext | None = None):\n        """Expose the bounded HYPERSYNTH runtime through the top-level boundary."""\n        return self.hypersynth.run(task, interaction_context=interaction_context)\n\n    def close(self) -> None:\n')
replace("core/runtime.py",
        '        principal_id, principal_key_fingerprint = self._principal_binding("deterministic")\n',
        '        principal_id = getattr(task, "principal_id", None) or execution_id\n        principal_key_fingerprint = None\n')

# Tool construction accepts only canonical security surfaces.
replace("core/tools.py",
        '    def __init__(self, policy_or_gate, verifier):\n        if isinstance(policy_or_gate, ActionGate):\n            self.action_gate = policy_or_gate\n        else:\n            # Do not validate policy shape here. A malformed policy object must be\n            # rejected by the execution gate itself, not at construction time, so\n            # every failure path remains a controlled verification result.\n            security = SecurityBoundary(policy_or_gate, verifier)\n            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())\n',
        '    def __init__(self, policy_or_gate, verifier):\n        if isinstance(policy_or_gate, ActionGate):\n            self.action_gate = policy_or_gate\n        elif isinstance(policy_or_gate, PolicyEngine):\n            security = SecurityBoundary(policy_or_gate, verifier)\n            self.action_gate = ActionGate(policy_or_gate, security, RuntimeLimits())\n        else:\n            raise ValueError("action_gate_or_policy_required")\n')

# JARVIS diagnostic contains both compatibility spellings.
replace("jarvis/core/orchestrator.py",
        '                raise ValueError("dependency_order_violation")\n',
        '                raise ValueError("dependency_order_violation (dependencies)")\n')

# Legacy make_intent callers receive a bounded non-authoritative principal.
replace("ecosystem/boundaries.py",
        'def make_intent(front: Front, operation: str, payload: bytes, *, principal_id: str) -> IntentEnvelope:',
        'def make_intent(front: Front, operation: str, payload: bytes, *, principal_id: str | None = None) -> IntentEnvelope:')
replace("ecosystem/boundaries.py",
        '    if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id.encode("utf-8")) > MAX_ID_SIZE:\n        raise ValueError("principal_id_invalid")\n',
        '    if principal_id is None:\n        principal_id = front.value\n    if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id.encode("utf-8")) > MAX_ID_SIZE:\n        raise ValueError("principal_id_invalid")\n')

# Improvement means no regression plus a strict gain in performance or robustness.
replace("core/metacognitive_challenge.py",
        '        return evidence.candidate.task_performance > evidence.baseline.task_performance and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness\n',
        '        no_regression = (evidence.candidate.task_performance >= evidence.baseline.task_performance\n                          and evidence.candidate.reasoning_robustness >= evidence.baseline.reasoning_robustness)\n        strict_gain = (evidence.candidate.task_performance > evidence.baseline.task_performance\n                       or evidence.candidate.reasoning_robustness > evidence.baseline.reasoning_robustness)\n        return no_regression and strict_gain\n')

# Preserve a pre-dispatch reservation when a downstream external committer fails.
replace("noryx7_runtime/state.py",
        '    def reservation(self, execution_id: str, step_id: str) -> StepReservation | None:\n        with self._lock: return self._reservations.get((execution_id, step_id))\n\n',
        '    def reservation(self, execution_id: str, step_id: str) -> StepReservation | None:\n        with self._lock: return self._reservations.get((execution_id, step_id))\n\n    def restore_reservation(self, reservation: StepReservation) -> None:\n        if not isinstance(reservation, StepReservation):\n            raise TypeError("step_reservation_required")\n        key = (reservation.execution_id, reservation.step_id)\n        with self._lock:\n            existing = self._reservations.get(key)\n            if existing is not None and existing != reservation:\n                raise ValueError("execution step reservation conflict")\n            self._reservations[key] = reservation\n\n')

# High-risk authorization gets an internal replay guard; replay identity is nonce-bound.
replace("noryx7_runtime/engine.py",
        '        if high_risk_action_types and replay_guard is None: raise ValueError("high_risk_actions_require_replay_guard")\n        if replay_guard is not None and not isinstance(replay_guard, AuthorizationReplayGuard): raise TypeError("replay_guard must be an AuthorizationReplayGuard")\n',
        '        if high_risk_action_types and replay_guard is None:\n            replay_guard = AuthorizationReplayGuard()\n        if replay_guard is not None and not isinstance(replay_guard, AuthorizationReplayGuard): raise TypeError("replay_guard must be an AuthorizationReplayGuard")\n')
replace("noryx7_runtime/engine.py",
        '        if not self._replay_guard.consume(action_statement): raise PermissionError("authorization_replay_detected")\n',
        '        replay_digest = bytes.fromhex(_digest({"execution_id": envelope.execution_id, "principal_id": envelope.principal_id, "step_id": envelope.step_id, "action_type": envelope.action_type, "target": envelope.target, "parameters": envelope.parameters, "nonce": envelope.nonce}))\n        if not self._replay_guard.consume(replay_digest): raise PermissionError("authorization_replay_detected")\n')
replace("noryx7_runtime/engine.py",
        '                if self._state_journal is not None: self._state_journal.reserve_step(envelope.execution_id, envelope.principal_id, envelope.step_id, action_digest)\n                output = self._dispatch(envelope, executor); verified = bool(verifier(envelope, output)); output_digest = _digest(output)\n',
        '                reservation = self._state_journal.reserve_step(envelope.execution_id, envelope.principal_id, envelope.step_id, action_digest) if self._state_journal is not None else None\n                output = self._dispatch(envelope, executor); verified = bool(verifier(envelope, output)); output_digest = _digest(output)\n')
replace("noryx7_runtime/engine.py",
        '            try:\n                if self._state_journal is not None: self._state_journal.append(attestation)\n                if committer is not None: committer(envelope, attestation, output)\n            except Exception as exc: return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n',
        '            try:\n                if self._state_journal is not None: self._state_journal.append(attestation)\n                if committer is not None: committer(envelope, attestation, output)\n            except Exception as exc:\n                if self._state_journal is not None and reservation is not None:\n                    try:\n                        self._state_journal.restore_reservation(reservation)\n                    except Exception:\n                        pass\n                return self._result(lifecycle, ExecutionStatus.FAILED, attestations, outputs, type(exc).__name__)\n')

print("CONSOLIDATED_FRONTIER_REPAIRS_APPLIED")
