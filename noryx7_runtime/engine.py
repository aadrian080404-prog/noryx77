from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence
from uuid import uuid4

from .adapters import ExecutionAdapter
from .capabilities import CapabilityBroker
from .contracts import ActionEnvelope, Attestation, ExecutionContext, ExecutionStatus, Intent, PlanStep
from .scheduler import Scheduler


Executor = Callable[[ActionEnvelope], Any]
Verifier = Callable[[ActionEnvelope, Any], bool]
Committer = Callable[[ActionEnvelope, Attestation, Any], None]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


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
    """Operational kernel for the NORYX7 data plane.

    Planning is delegated to the deterministic scheduler. Effects may be
    delegated to a capability-backed adapter; the legacy executor remains an
    explicit test/compatibility seam and is never selected implicitly.
    """

    def __init__(
        self,
        *,
        max_actions: int = 32,
        clock: Callable[[], float] = time.monotonic,
        scheduler: Scheduler | None = None,
        adapter: ExecutionAdapter | None = None,
    ) -> None:
        if isinstance(max_actions, bool) or not isinstance(max_actions, int) or max_actions < 0:
            raise ValueError("max_actions must be a non-negative integer")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if scheduler is not None and not isinstance(scheduler, Scheduler):
            raise TypeError("scheduler must be a Scheduler")
        if adapter is not None and not callable(getattr(adapter, "execute", None)):
            raise TypeError("adapter must expose execute")
        self._max_actions = max_actions
        self._clock = clock
        self._scheduler = scheduler or Scheduler()
        self._adapter = adapter

    def execute(
        self,
        intent: Intent,
        steps: Sequence[PlanStep],
        *,
        executor: Executor | None = None,
        verifier: Verifier,
        committer: Committer | None = None,
        timeout_seconds: float = 30.0,
        execution_id: str | None = None,
    ) -> RuntimeResult:
        if not isinstance(intent, Intent):
            raise TypeError("intent must be an Intent")
        if not isinstance(steps, Sequence):
            raise TypeError("steps must be a sequence")
        if not callable(verifier):
            raise TypeError("verifier must be callable")
        if executor is not None and not callable(executor):
            raise TypeError("executor must be callable")
        if self._adapter is None and executor is None:
            raise ValueError("an execution adapter or executor is required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
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
        ordered = tuple(item.step for item in self._scheduler.schedule(steps))
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
            try:
                action_digest = _digest({
                    "execution_id": envelope.execution_id,
                    "principal_id": envelope.principal_id,
                    "step_id": envelope.step_id,
                    "action_type": envelope.action_type,
                    "target": envelope.target,
                    "parameters": envelope.parameters,
                    "nonce": envelope.nonce,
                })
                dispatch = self._adapter.execute if self._adapter is not None else executor
                output = dispatch(envelope)
                verified = bool(verifier(envelope, output))
                output_digest = _digest(output)
            except Exception as exc:
                return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), type(exc).__name__)

            attestation = Attestation(
                execution_id=envelope.execution_id,
                principal_id=envelope.principal_id,
                step_id=envelope.step_id,
                agent_id="adapter",
                action_digest=action_digest,
                output_digest=output_digest,
                verified=verified,
                detail="verified" if verified else "verification_failed",
            )
            if not verified:
                attestations.append(attestation)
                return RuntimeResult(context.execution_id, ExecutionStatus.REJECTED, tuple(attestations), tuple(outputs), "result_verification_failed")

            if committer is not None:
                try:
                    committer(envelope, attestation, output)
                except Exception as exc:
                    return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), type(exc).__name__)
            attestations.append(attestation)
            outputs.append(output)

        return RuntimeResult(context.execution_id, ExecutionStatus.SUCCEEDED, tuple(attestations), tuple(outputs))

    @staticmethod
    def _topological_order(steps: Iterable[PlanStep]) -> tuple[PlanStep, ...]:
        return tuple(item.step for item in Scheduler().schedule(tuple(steps)))
