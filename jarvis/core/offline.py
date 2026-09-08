"""JARVIS bindings for the shared fail-closed offline runtime."""
from __future__ import annotations

from dataclasses import dataclass

from core.offline import OfflineExecution, OfflineRuntime, OfflineSnapshot
from jarvis.core.contracts import ActionResult, Plan, Request
from jarvis.core.policy import Policy
from jarvis.core.recovery import RecoveryController
from jarvis.core.state import JarvisState, JarvisStateStore


class JarvisOfflinePolicy:
    def __init__(self, policy: Policy):
        if not isinstance(policy, Policy):
            raise TypeError("jarvis_policy_required")
        self._policy = policy

    def authorize(self, *, principal_id: str, operation: str, offline: bool) -> bool:
        if offline is not True or not principal_id or operation != "jarvis.execute":
            return False
        return True


class JarvisOfflineVerifier:
    def verify(self, result: object) -> bool:
        if not isinstance(result, tuple) or not result:
            return False
        return all(isinstance(item, ActionResult) and item.success is True for item in result)


@dataclass
class JarvisOfflineBinding:
    runtime: OfflineRuntime
    state: JarvisStateStore

    @classmethod
    def build(cls, *, policy: Policy, recovery: RecoveryController, state: JarvisStateStore,
              cipher, clock, snapshot_authenticator):
        return cls(
            runtime=OfflineRuntime(
                recovery=recovery,
                policy=JarvisOfflinePolicy(policy),
                verifier=JarvisOfflineVerifier(),
                cipher=cipher,
                clock=clock,
                snapshot_authenticator=snapshot_authenticator,
            ),
            state=state,
        )

    def install_snapshot(self, snapshot: OfflineSnapshot) -> None:
        self.runtime.install_snapshot(snapshot)

    def execute(self, *, request: Request, plan: Plan, local_execute, snapshot_state_version: str) -> object:
        if not isinstance(request, Request) or not isinstance(plan, Plan):
            raise TypeError("jarvis_request_and_plan_required")
        if plan.request_id != request.request_id:
            raise PermissionError("request_identity_mismatch")
        execution_id = request.request_id
        payload = request.text.encode("utf-8")
        execution = OfflineExecution(
            execution_id=execution_id,
            principal_id=request.principal_id,
            operation="jarvis.execute",
            capability="jarvis.execute",
            payload_digest=__import__("hashlib").sha256(payload).hexdigest(),
            base_state_version=snapshot_state_version,
        )

        def commit(_execution: OfflineExecution, results: tuple[ActionResult, ...]) -> None:
            state = JarvisState(
                execution_id=execution_id,
                request_id=request.request_id,
                principal_id=request.principal_id,
                request_digest=self.state.digest_request(request.text),
                completed_steps=[result.step_id for result in results],
                results=[{"step_id": result.step_id, "success": result.success, "output": result.output} for result in results],
                status="verified",
            )
            self.state.commit(state, verified_results=True, execution_id=execution_id, request_id=request.request_id)

        return self.runtime.execute(
            execution=execution,
            payload=payload,
            execute=lambda: tuple(local_execute(step) for step in plan.steps),
            commit=commit,
        )
