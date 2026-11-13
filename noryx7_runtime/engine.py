from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence
from uuid import uuid4

from core.authorization_replay import AuthorizationReplayGuard
from core.identity import AgentIdentity, IdentityRegistry
from core.multiauth import SignedApprovalAuthority, SignedAuthorizationProof
from .adapters import ExecutionAdapter
from .attestation import AttestationSigner, attestation_digest, signed_attestation
from .contracts import ActionEnvelope, Attestation, ExecutionContext, ExecutionStatus, Intent, PlanStep
from .lifecycle import ExecutionLifecycle
from .scheduler import Scheduler
from .state import StateJournal

Executor = Callable[[ActionEnvelope], Any]
Verifier = Callable[[ActionEnvelope, Any], bool]
Committer = Callable[[ActionEnvelope, Attestation, Any], None]
AuthorizationProvider = Callable[[ActionEnvelope, bytes], SignedAuthorizationProof | None]
_ZERO_DIGEST = "0" * 64
MANDATORY_HIGH_RISK_ACTION_TYPES = frozenset({
    "payments", "flights", "insurance", "financial",
    "execute_external", "publish", "delete_external", "system_change",
    "jarvis_capability",
})

def _canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
def _digest(value: Any) -> str: return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class RuntimeResult:
    execution_id: str
    status: ExecutionStatus
    attestations: tuple[Attestation, ...]
    outputs: tuple[Any, ...]
    error: str | None = None

class RuntimeEngine:
    """Operational kernel for the NORYX7 data plane."""
    def __init__(self, *, max_actions: int = 32, clock: Callable[[], float] = time.monotonic, scheduler: Scheduler | None = None, adapter: ExecutionAdapter | None = None, attestation_signer: AttestationSigner | None = None, identity_registry: IdentityRegistry | None = None, runtime_id: str | None = None, state_journal: StateJournal | None = None, multi_auth_authority: SignedApprovalAuthority | None = None, authorization_provider: AuthorizationProvider | None = None, high_risk_action_types: set[str] | frozenset[str] | None = None, authorization_epoch: int = 0, replay_guard: AuthorizationReplayGuard | None = None, require_authenticated_replay_guard: bool = False, require_durable_state_journal: bool = False) -> None:
        if isinstance(max_actions, bool) or not isinstance(max_actions, int) or max_actions < 0: raise ValueError("max_actions must be a non-negative integer")
        if not callable(clock): raise TypeError("clock must be callable")
        if scheduler is not None and not isinstance(scheduler, Scheduler): raise TypeError("scheduler must be a Scheduler")
        if adapter is not None and not callable(getattr(adapter, "execute", None)): raise TypeError("adapter must expose execute")
        if attestation_signer is not None and not callable(getattr(attestation_signer, "sign", None)): raise TypeError("attestation_signer must expose sign")
        if adapter is not None and attestation_signer is None: raise ValueError("adapter-backed execution requires attestation_signer")
        if identity_registry is not None and not isinstance(identity_registry, IdentityRegistry): raise TypeError("identity_registry must be an IdentityRegistry")
        if state_journal is not None and not isinstance(state_journal, StateJournal): raise TypeError("state_journal must be a StateJournal")
        if runtime_id is not None and (not isinstance(runtime_id, str) or not runtime_id): raise ValueError("runtime_id must be a non-empty string")
        if multi_auth_authority is not None and not isinstance(multi_auth_authority, SignedApprovalAuthority): raise TypeError("multi_auth_authority must be a SignedApprovalAuthority")
        if authorization_provider is not None and not callable(authorization_provider): raise TypeError("authorization_provider must be callable")
        if multi_auth_authority is not None and authorization_provider is None: raise ValueError("multi_auth_authority requires authorization_provider")
        if authorization_provider is not None and multi_auth_authority is None: raise ValueError("authorization_provider requires multi_auth_authority")
        if not isinstance(authorization_epoch, int) or isinstance(authorization_epoch, bool) or authorization_epoch < 0: raise ValueError("authorization_epoch must be a non-negative integer")
        high_risk_action_types = frozenset() if high_risk_action_types is None else high_risk_action_types
        if not isinstance(high_risk_action_types, (set, frozenset)) or any(not isinstance(item, str) or not item for item in high_risk_action_types): raise TypeError("high_risk_action_types must contain non-empty strings")
        custom_high_risk_action_types = frozenset(high_risk_action_types)
        high_risk_action_types = custom_high_risk_action_types | MANDATORY_HIGH_RISK_ACTION_TYPES
        if replay_guard is not None and not isinstance(replay_guard, AuthorizationReplayGuard): raise TypeError("replay_guard must be an AuthorizationReplayGuard")
        if not isinstance(require_authenticated_replay_guard, bool): raise TypeError("require_authenticated_replay_guard must be bool")
        if not isinstance(require_durable_state_journal, bool): raise TypeError("require_durable_state_journal must be bool")
        if require_durable_state_journal and (state_journal is None or not getattr(state_journal, "durable", False)):
            raise ValueError("durable_runtime_state_journal_required")
        if require_authenticated_replay_guard:
            if replay_guard is None or not replay_guard.durable or not getattr(replay_guard, "integrity_protected", False):
                raise ValueError("high_risk_actions_require_authenticated_replay_guard")
        if custom_high_risk_action_types:
            if replay_guard is None:
                raise ValueError("high_risk_actions_require_replay_guard")
            if not replay_guard.durable:
                raise ValueError("high_risk_actions_require_durable_replay_guard")
        if adapter is not None and identity_registry is not None:
            public_key = getattr(attestation_signer, "public_key_bytes", None)
            if not isinstance(public_key, bytes): raise ValueError("identity-bound execution requires signer public key")
            if not identity_registry.is_trusted(AgentIdentity(str(adapter.agent_id), public_key)): raise PermissionError("adapter identity is not trusted")
        self._max_actions, self._clock = max_actions, clock; self._scheduler, self._adapter = scheduler or Scheduler(), adapter
        self._attestation_signer, self._identity_registry = attestation_signer, identity_registry; self._state_journal = state_journal; self._runtime_id = runtime_id or uuid4().hex
        self._multi_auth_authority, self._authorization_provider = multi_auth_authority, authorization_provider; self._high_risk_action_types = frozenset(high_risk_action_types); self._authorization_epoch = authorization_epoch; self._replay_guard = replay_guard; self._require_authenticated_replay_guard = require_authenticated_replay_guard; self._require_durable_state_journal = require_durable_state_journal
        if state_journal is not None and state_journal.runtime_id not in (None, self._runtime_id): raise ValueError("state journal runtime identity mismatch")
    @property
    def runtime_id(self) -> str: return self._runtime_id
    @staticmethod
    def _result(lifecycle: ExecutionLifecycle, status: ExecutionStatus, attestations: Sequence[Attestation], outputs: Sequence[Any], error: str | None = None) -> RuntimeResult:
        final = lifecycle.transition(status)
        return RuntimeResult(final.execution_id, final.status, tuple(attestations), tuple(outputs), error)
    def _dispatch(self, envelope: ActionEnvelope, executor: Executor | None, deadline_monotonic: float | None = None) -> Any:
        if self._adapter is None:
            if executor is None:
                raise RuntimeError("execution dispatch is unavailable")
            return executor(envelope)

        def dispatch_adapter() -> Any:
            bounded = getattr(self._adapter, "execute_with_timeout", None)
            if deadline_monotonic is not None and callable(bounded):
                remaining = deadline_monotonic - self._clock()
                if remaining <= 0:
                    raise TimeoutError("execution_deadline_exceeded_before_dispatch")
                return bounded(envelope, remaining)
            return self._adapter.execute(envelope)

        if self._identity_registry is None:
            return dispatch_adapter()
        public_key = getattr(self._attestation_signer, "public_key_bytes", None)
        if not isinstance(public_key, bytes):
            raise PermissionError("identity-bound execution requires signer public key")
        def run_if_trusted(identity: AgentIdentity) -> Any:
            if identity.public_key != public_key:
                raise PermissionError("adapter identity key mismatch")
            # Keep revocation serialized with the authorized side effect. For
            # ProcessExecutionAdapter, the runtime deadline bounds this section.
            return dispatch_adapter()
        return self._identity_registry.with_trusted_identity(str(self._adapter.agent_id), run_if_trusted)
    def _authorize_high_risk(
        self,
        envelope: ActionEnvelope,
        action_statement: bytes,
        replay_token: bytes,
    ) -> None:
        if envelope.risk_class != "high" and envelope.action_type not in self._high_risk_action_types:
            return

        if (
            self._multi_auth_authority is None
            or self._authorization_provider is None
        ):
            raise PermissionError("multi_auth_required")

        if self._replay_guard is None or not self._replay_guard.durable:
            raise PermissionError("durable_replay_guard_required")
        if self._require_authenticated_replay_guard and not getattr(
            self._replay_guard, "integrity_protected", False
        ):
            raise PermissionError("authenticated_replay_guard_required")

        try:
            proof = self._authorization_provider(
                envelope,
                action_statement,
            )
        except Exception as exc:
            raise PermissionError(
                "authorization_provider_failed"
            ) from exc

        if not isinstance(proof, SignedAuthorizationProof):
            raise PermissionError("authorization_proof_required")

        if not self._multi_auth_authority.verify(
            proof,
            action_id=envelope.execution_id,
            epoch=self._authorization_epoch,
            action_statement=action_statement,
        ):
            raise PermissionError("authorization_proof_invalid")

        if not self._replay_guard.consume(
            replay_token,
            expires_at=proof.expires_at,
            now=time.time(),
        ):
            raise PermissionError("authorization_replay_detected")

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

        # ----------------------------
        # Input boundary
        # ----------------------------
        if not isinstance(intent, Intent):
            raise TypeError("intent must be an Intent")

        if not isinstance(steps, Sequence):
            raise TypeError("steps must be a sequence")

        if not callable(verifier):
            raise TypeError("verifier must be callable")

        if executor is not None and not callable(executor):
            raise TypeError("executor must be callable")

        if self._adapter is None and executor is None:
            raise ValueError(
                "an execution adapter or executor is required"
            )

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")

        # ----------------------------
        # Lifecycle
        # ----------------------------
        lifecycle = ExecutionLifecycle(
            execution_id or uuid4().hex,
            intent.principal_id,
        )

        if len(steps) > self._max_actions:
            return self._result(
                lifecycle,
                ExecutionStatus.REJECTED,
                (),
                (),
                "action_budget_exceeded",
            )

        lifecycle = lifecycle.transition(ExecutionStatus.RUNNING)

        context = ExecutionContext(
            lifecycle.execution_id,
            intent.principal_id,
            self._clock() + timeout_seconds,
            self._max_actions,
            ExecutionStatus.RUNNING,
        )

        # Scheduler exceptions must escape as contract errors.
        ordered = tuple(
            item.step
            for item in self._scheduler.schedule(tuple(steps))
        )

        try:
            plan_digest = _digest([
                {
                    "step_id": step.step_id,
                    "action_type": step.action_type,
                    "target": step.target,
                    "parameters": dict(step.parameters),
                    "dependencies": sorted(step.dependencies),
                    "risk_class": step.risk_class,
                }
                for step in sorted(ordered, key=lambda item: item.step_id)
            ])
        except (TypeError, ValueError, OverflowError):
            return self._result(
                lifecycle,
                ExecutionStatus.REJECTED,
                (),
                (),
                "plan_digest_invalid",
            )

        attestations: list[Attestation] = []
        outputs: list[Any] = []
        previous_attestation_digest = _ZERO_DIGEST

        # ----------------------------
        # Deterministic execution
        # ----------------------------
        for plan_step in ordered:

            if self._clock() > context.deadline_monotonic:
                return self._result(
                    lifecycle,
                    ExecutionStatus.CANCELLED,
                    attestations,
                    outputs,
                    "deadline_exceeded",
                )

            envelope = ActionEnvelope(
                context.execution_id,
                context.principal_id,
                plan_step.step_id,
                plan_step.action_type,
                plan_step.target,
                dict(plan_step.parameters),
                uuid4().hex,
                plan_step.risk_class,
                plan_digest,
            )

            reservation = None

            try:
                # Concrete action digest includes nonce.
                action_digest = _digest(
                    {
                        "execution_id": envelope.execution_id,
                        "principal_id": envelope.principal_id,
                        "step_id": envelope.step_id,
                        "action_type": envelope.action_type,
                        "target": envelope.target,
                        "parameters": envelope.parameters,
                        "risk_class": envelope.risk_class,
                        "plan_digest": envelope.plan_digest,
                        "nonce": envelope.nonce,
                    }
                )

                # Authorization statement is stable across retries and is the
                # exact statement signed by the approvers. Replay protection
                # must consume this identity, not a per-attempt nonce digest.
                authorization_statement = bytes.fromhex(
                    _digest(
                        {
                            "execution_id": envelope.execution_id,
                            "principal_id": envelope.principal_id,
                            "step_id": envelope.step_id,
                            "action_type": envelope.action_type,
                            "target": envelope.target,
                            "parameters": envelope.parameters,
                            "risk_class": envelope.risk_class,
                            "plan_digest": envelope.plan_digest,
                        }
                    )
                )

                replay_token = authorization_statement

                self._authorize_high_risk(
                    envelope,
                    authorization_statement,
                    replay_token,
                )

                # Reserve BEFORE dispatch. This prevents duplicate side effects.
                if self._state_journal is not None:
                    reservation = self._state_journal.reserve_step(
                        envelope.execution_id,
                        envelope.principal_id,
                        envelope.step_id,
                        action_digest,
                    )

                output = self._dispatch(envelope, executor, context.deadline_monotonic)

                # Verification is performed before any commit.
                verified = bool(verifier(envelope, output))

                # Force JSON-compatible output at the attestation boundary.
                output_digest = _digest(output)

                if self._adapter is not None:
                    agent_id = str(
                        getattr(self._adapter, "agent_id", "executor")
                    )
                else:
                    agent_id = "executor"

                if self._attestation_signer is not None:
                    public_key = getattr(
                        self._attestation_signer,
                        "public_key_bytes",
                        None,
                    )
                else:
                    public_key = None

                if isinstance(public_key, bytes):
                    fingerprint = hashlib.sha256(
                        public_key
                    ).hexdigest()
                else:
                    fingerprint = hashlib.sha256(
                        b"legacy-executor"
                    ).hexdigest()

                attestation = Attestation(
                    context.execution_id,
                    context.principal_id,
                    plan_step.step_id,
                    agent_id,
                    fingerprint,
                    action_digest,
                    output_digest,
                    verified,
                    "verified" if verified else "verification_failed",
                    previous_attestation_digest=previous_attestation_digest,
                    runtime_id=self._runtime_id,
                )

                if self._attestation_signer is not None:
                    attestation = signed_attestation(
                        attestation,
                        self._attestation_signer,
                    )

            except Exception as exc:
                # Reservation intentionally remains if dispatch/commit has
                # crossed the side-effect boundary. This is required for
                # re-execution protection.
                return self._result(
                    lifecycle,
                    ExecutionStatus.FAILED,
                    attestations,
                    outputs,
                    type(exc).__name__,
                )

            # ----------------------------
            # Verification rejection
            # ----------------------------
            if not verified:
                return self._result(
                    lifecycle,
                    ExecutionStatus.REJECTED,
                    (*attestations, attestation),
                    outputs,
                    "result_verification_failed",
                )

            # Adapter-backed execution requires cryptographic attestation.
            if (
                self._adapter is not None
                and not attestation.signature
            ):
                return self._result(
                    lifecycle,
                    ExecutionStatus.FAILED,
                    attestations,
                    outputs,
                    "unsigned_attestation",
                )

            # ----------------------------
            # Commit boundary
            # ----------------------------
            try:
                if self._state_journal is not None:
                    self._state_journal.append(attestation)

                if committer is not None:
                    committer(
                        envelope,
                        attestation,
                        output,
                    )

            except Exception as exc:
                # The journal append consumes the reservation. If the
                # external commit boundary fails afterwards, restore the
                # exact pre-dispatch reservation so the execution step
                # remains permanently blocked from re-dispatch.
                if self._state_journal is not None and reservation is not None:
                    try:
                        self._state_journal.restore_reservation(reservation)
                    except Exception as restore_exc:
                        # Losing the reservation after journal consumption would
                        # reopen the execution step for duplicate dispatch. Fail closed.
                        raise RuntimeError("reservation_restore_failed") from restore_exc
                return self._result(
                    lifecycle,
                    ExecutionStatus.FAILED,
                    attestations,
                    outputs,
                    type(exc).__name__,
                )

            attestations.append(attestation)
            outputs.append(output)

            if attestation.signature:
                previous_attestation_digest = attestation_digest(
                    attestation
                )

        return self._result(
            lifecycle,
            ExecutionStatus.SUCCEEDED,
            attestations,
            outputs,
        )

    @staticmethod
    def _topological_order(steps: Iterable[PlanStep]) -> tuple[PlanStep, ...]: return tuple(item.step for item in Scheduler().schedule(tuple(steps)))
