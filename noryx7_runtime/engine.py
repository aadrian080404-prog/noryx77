from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence
from uuid import uuid4

from core.identity import AgentIdentity, IdentityRegistry

from .adapters import ExecutionAdapter
from .attestation import AttestationSigner, signed_attestation
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
    """Operational kernel for the NORYX7 data plane."""

    def __init__(
        self,
        *,
        max_actions: int = 32,
        clock: Callable[[], float] = time.monotonic,
        scheduler: Scheduler | None = None,
        adapter: ExecutionAdapter | None = None,
        attestation_signer: AttestationSigner | None = None,
        identity_registry: IdentityRegistry | None = None,
    ) -> None:
        if isinstance(max_actions, bool) or not isinstance(max_actions, int) or max_actions < 0:
            raise ValueError("max_actions must be a non-negative integer")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if scheduler is not None and not isinstance(scheduler, Scheduler):
            raise TypeError("scheduler must be a Scheduler")
        if adapter is not None and not callable(getattr(adapter, "execute", None)):
            raise TypeError("adapter must expose execute")
        if attestation_signer is not None and not callable(getattr(attestation_signer, "sign", None)):
            raise TypeError("attestation_signer must expose sign")
        if adapter is not None and attestation_signer is None:
            raise ValueError("adapter-backed execution requires attestation_signer")
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry):
            raise TypeError("identity_registry must be an IdentityRegistry")
        if adapter is not None and identity_registry is not None:
            public_key = getattr(attestation_signer, "public_key_bytes", None)
            if not isinstance(public_key, bytes):
                raise ValueError("identity-bound execution requires signer public key")
            identity = AgentIdentity(str(adapter.agent_id), public_key)
            if not identity_registry.is_trusted(identity):
                raise PermissionError("adapter identity is not trusted")
        self._max_actions = max_actions
        self._clock = clock
        self._scheduler = scheduler or Scheduler()
        self._adapter = adapter
        self._attestation_signer = attestation_signer
        self._identity_registry = identity_registry

    def _dispatch(self, envelope: ActionEnvelope, executor: Executor | None) -> Any:
        dispatch = self._adapter.execute if self._adapter is not None else executor
        if dispatch is None:
            raise RuntimeError("execution dispatch is unavailable")
        if self._adapter is None or self._identity_registry is None:
            return dispatch(envelope)

        public_key = getattr(self._attestation_signer, "public_key_bytes", None)
        if not isinstance(public_key, bytes):
            raise PermissionError("identity-bound execution requires signer public key")
        agent_id = str(self._adapter.agent_id)

        def run_if_trusted(identity: AgentIdentity) -> Any:
            if identity.public_key != public_key:
                raise PermissionError("adapter identity key mismatch")
            return dispatch(envelope)

        # Hold the identity trust-anchor lock through the bounded dispatch. This
        # gives revoke-vs-dispatch a single linearization point: either the
        # effect starts before revocation, or revocation wins and no effect runs.
        return self._identity_registry.with_trusted_identity(agent_id, run_if_trusted)

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
                output = self._dispatch(envelope, executor)
                verified = bool(verifier(envelope, output))
                output_digest = _digest(output)
                agent_id = str(getattr(self._adapter, "agent_id", "executor")) if self._adapter is not None else "executor"
                if self._attestation_signer is not None:
                    public_key = getattr(self._attestation_signer, "public_key_bytes", None)
                    if not isinstance(public_key, bytes):
                        raise ValueError("attestation signer does not expose public key")
                    fingerprint = hashlib.sha256(public_key).hexdigest()
                else:
                    fingerprint = hashlib.sha256(b"legacy-executor").hexdigest()
                attestation = Attestation(
                    execution_id=envelope.execution_id,
                    principal_id=envelope.principal_id,
                    step_id=envelope.step_id,
                    agent_id=agent_id,
                    agent_key_fingerprint=fingerprint,
                    action_digest=action_digest,
                    output_digest=output_digest,
                    verified=verified,
                    detail="verified" if verified else "verification_failed",
                )
                if self._attestation_signer is not None:
                    attestation = signed_attestation(attestation, self._attestation_signer)
            except Exception as exc:
                return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), type(exc).__name__)

            if not verified:
                attestations.append(attestation)
                return RuntimeResult(context.execution_id, ExecutionStatus.REJECTED, tuple(attestations), tuple(outputs), "result_verification_failed")

            if self._adapter is not None and not attestation.signature:
                return RuntimeResult(context.execution_id, ExecutionStatus.FAILED, tuple(attestations), tuple(outputs), "unsigned_attestation")

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
