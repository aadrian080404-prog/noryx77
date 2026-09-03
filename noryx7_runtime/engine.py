from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import uuid4

from .contracts import ActionEnvelope, Attestation, ExecutionContext, ExecutionStatus, Intent, PlanStep


Executor = Callable[[ActionEnvelope], Any]
Verifier = Callable[[ActionEnvelope, Any], bool]
Committer = Callable[[ActionEnvelope, Attestation, Any], None]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RuntimeResult:
    execution_id: str
    status: ExecutionStatus
    attestations: tuple[Attestation, ...]
    outputs: tuple[Any, ...]
    error: str | None = None


class RuntimeEngine:
    """Small operational kernel for the future NORYX7 data plane.

    The engine intentionally owns orchestration, not authority. A production
    adapter is expected to put cryptographic authorization in front of its
    executor and to perform privileged effects only after that authorization.
    """

    def __init__(
        self,
        *,
        max_actions: int = 32,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_actions < 0:
            raise ValueError("max_actions must be non-negative")
        self._max_actions = max_actions
        self._clock = clock

    def execute(
        self,
        intent: Intent,
        steps: Sequence[PlanStep],
        *,
        executor: Executor,
        verifier: Verifier,
        committer: Committer | None = None,
        timeout_seconds: float = 30.0,
        execution_id: str | None = None,
    ) -> RuntimeResult:
        if not isinstance(intent, Intent):
            raise TypeError("intent must be an Intent")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if len(steps) > self._max_actions:
            return RuntimeResult(execution_id or uuid4().hex, ExecutionStatus.REJECTED, (), (), "action_budget_exceeded")

        context = ExecutionContext(
            execution_id=execution_id or uuid4().hex,
            principal_id=intent.principal_id,
            deadline_monotonic=self._clock() + timeout_seconds,
            max_actions=self._max_actions,
            status=ExecutionStatus.RUNNING,
        )
        ordered = self._topological_order(steps)
        attestations: list[Attestation] = []
        outputs: list[Any] = []

        for step in ordered:
            if self._clock() > context.deadline_monotonic:
                return RuntimeResult(context.execution_id, ExecutionStatus.CANCELLED, tuple(attestations), tuple(outputs), "deadline_exceeded")

            envelope = ActionEnvelope(
                execution_id=context.execution_id,
                principal_id=context.principal_id,
                step_id=step.step_id,
                action_type=step.action_type,
                target=step.target,
                parameters=dict(step.parameters),
                nonce=uuid4().hex,
            )
            action_digest = _digest({
                "execution_id": envelope.execution_id,
                "principal_id": envelope.principal_id,
                "step_id": envelope.step_id,
                "action_type": envelope.action_type,
                "target": envelope.target,
                "parameters": envelope.parameters,
                "nonce": envelope.nonce,
            })

            try:
                output = executor(envelope)
                verified = bool(verifier(envelope, output))
            except Exception as exc:  # fail closed at the runtime boundary
                return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), type(exc).__name__)

            attestation = Attestation(
                execution_id=envelope.execution_id,
                principal_id=envelope.principal_id,
                step_id=envelope.step_id,
                agent_id="adapter",
                action_digest=action_digest,
                output_digest=_digest(output),
                verified=verified,
                detail="verified" if verified else "verification_failed",
            )
            attestations.append(attestation)
            if not verified:
                return RuntimeResult(context.execution_id, ExecutionStatus.REJECTED, tuple(attestations), tuple(outputs), "result_verification_failed")

            if committer is not None:
                try:
                    committer(envelope, attestation, output)
                except Exception as exc:
                    return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), type(exc).__name__)
            outputs.append(output)

        return RuntimeResult(context.execution_id, ExecutionStatus.SUCCEEDED, tuple(attestations), tuple(outputs))

    @staticmethod
    def _topological_order(steps: Iterable[PlanStep]) -> tuple[PlanStep, ...]:
        items = tuple(steps)
        by_id = {step.step_id: step for step in items}
        if len(by_id) != len(items):
            raise ValueError("duplicate step id")
        for step in items:
            missing = [dep for dep in step.dependencies if dep not in by_id]
            if missing:
                raise ValueError(f"missing dependency: {missing[0]}")

        ordered: list[PlanStep] = []
        remaining = set(by_id)
        while remaining:
            ready = sorted(step_id for step_id in remaining if all(dep not in remaining for dep in by_id[step_id].dependencies))
            if not ready:
                raise ValueError("cyclic plan dependencies")
            ordered.extend(by_id[step_id] for step_id in ready)
            remaining.difference_update(ready)
        return tuple(ordered)
