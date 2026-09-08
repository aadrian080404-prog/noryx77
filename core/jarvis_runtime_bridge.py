from __future__ import annotations

from typing import Any

from core.contracts import ActionSpec, VerificationResult
from core.actions import AuthorizationAuthority, AuthorizationGrant
from core.identity import AgentIdentity
from core.tools import ToolExecutor
from core.verification import VerificationEngine
from jarvis.core.contracts import ActionResult, Plan, PlanStep, Request
from noryx7_runtime.contracts import Intent, PlanStep as RuntimePlanStep
from noryx7_runtime.engine import RuntimeEngine


class JarvisRuntimeBridge:
    """
    Canonical JARVIS -> NORYX7 execution bridge.

    JARVIS remains responsible for request/plan semantics.
    RuntimeEngine remains the operational execution kernel.
    ToolExecutor remains the canonical capability boundary.
    """

    def __init__(
        self,
        *,
        runtime_engine: RuntimeEngine,
        tool_executor: ToolExecutor,
        verifier: VerificationEngine | None = None,
        authorization: AuthorizationAuthority | None = None,
        principal: AgentIdentity | None = None,
        policy: Any | None = None,
    ) -> None:
        if not isinstance(runtime_engine, RuntimeEngine):
            raise TypeError("runtime_engine_required")
        if not isinstance(tool_executor, ToolExecutor):
            raise TypeError("tool_executor_required")

        self.runtime_engine = runtime_engine
        self.tool_executor = tool_executor
        self.verifier = verifier or VerificationEngine()
        if not isinstance(authorization, AuthorizationAuthority):
            raise TypeError("authorization_authority_required")
        if not isinstance(principal, AgentIdentity):
            raise TypeError("agent_identity_required")
        if policy is None or not callable(getattr(policy, "authorize", None)):
            raise TypeError("jarvis_policy_required")
        self.authorization = authorization
        self.principal = principal
        self.policy = policy

    @staticmethod
    def _runtime_step(step: PlanStep) -> RuntimePlanStep:
        return RuntimePlanStep(
            step_id=step.step_id,
            action_type=step.capability,
            target=step.target,
            parameters=dict(step.parameters),
            dependencies=tuple(step.dependencies),
        )

    def execute(self, request: Request, plan: Plan) -> tuple[ActionResult, ...]:
        if not isinstance(request, Request):
            raise TypeError("request_required")
        if not isinstance(plan, Plan):
            raise TypeError("plan_required")
        if request.request_id != plan.request_id:
            raise PermissionError("request_plan_mismatch")

        runtime_steps = tuple(
            self._runtime_step(step)
            for step in plan.steps
        )

        intent = Intent(
            text=request.text,
            principal_id=request.principal_id,
            intent_id=request.request_id,
        )

        def executor(envelope: Any) -> Any:
            if not self.policy.authorize(
                request.principal_id,
                envelope.action_type,
                envelope.target,
            ):
                raise PermissionError("capability_denied")

            action = ActionSpec(
                action_id=f"{envelope.execution_id}:{envelope.step_id}:{envelope.nonce}",
                # JARVIS capabilities and Core action types are distinct
                # namespaces. The Core sees an explicitly delegated JARVIS
                # action while the original capability remains bound through
                # target, parameters, grant, identity and JARVIS Policy.
                action_type="jarvis_capability",
                target=envelope.target,
                parameters={
                    **dict(envelope.parameters),
                    "__jarvis_step_id": envelope.step_id,
                    "__jarvis_capability": envelope.action_type,
                },
                requires_authorization=True,
                execution_id=envelope.execution_id,
            )

            grant = self.authorization.issue(
                action,
                envelope.execution_id,
                principal=self.principal,
            )

            output, verification = self.tool_executor.execute(
                action,
                execution_id=envelope.execution_id,
                grant=grant,
                principal=self.principal,
            )

            if not isinstance(verification, VerificationResult):
                raise TypeError("invalid_tool_verification")

            if not verification.valid:
                raise PermissionError(
                    verification.reason or "tool_execution_rejected"
                )

            # JARVIS capabilities return ActionResult. RuntimeEngine must
            # receive only the actual payload, not the JARVIS wrapper.
            if not isinstance(output, ActionResult):
                raise TypeError("jarvis_capability_result_required")

            if not output.success:
                raise PermissionError(
                    output.error or "jarvis_capability_failed"
                )

            return output.output

        def verify(envelope: Any, output: Any) -> bool:
            try:
                result = self.verifier.verify_output(
                    output,
                    stage="runtime_result",
                )
                return (
                    isinstance(result, VerificationResult)
                    and result.is_well_formed()
                    and result.valid
                )
            except Exception:
                return False

        runtime_result = self.runtime_engine.execute(
            intent,
            runtime_steps,
            executor=executor,
            verifier=verify,
            execution_id=request.request_id,
        )

        results: list[ActionResult] = []

        for step, output in zip(
            plan.steps,
            runtime_result.outputs,
        ):
            results.append(
                ActionResult(
                    step_id=step.step_id,
                    success=True,
                    output=output,
                )
            )

        if runtime_result.status.value != "succeeded":
            completed = {result.step_id for result in results}

            for step in plan.steps:
                if step.step_id not in completed:
                    results.append(
                        ActionResult(
                            step_id=step.step_id,
                            success=False,
                            error=runtime_result.error or runtime_result.status.value,
                        )
                    )

            results = [
                result
                for result in results
                if result.step_id in {
                    step.step_id for step in plan.steps
                }
            ]

        return tuple(results)
