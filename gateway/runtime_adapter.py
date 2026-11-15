from __future__ import annotations

from uuid import uuid4

from core.contracts import TaskSpec
from core.operational_runtime import OperationalNORYXRuntime


class RuntimeAdapter:
    """Translate a bootstrap-authenticated client label into a bounded runtime task.

    The client label is diagnostic metadata only. It is not a user, device,
    tenant, ownership, or authorization principal.
    """

    def __init__(self, runtime: OperationalNORYXRuntime | None = None):
        self.runtime = runtime or OperationalNORYXRuntime()

    def execute(
        self,
        *,
        client_label: str,
        text: str,
        execution_id: str | None = None,
    ) -> dict:
        if not isinstance(client_label, str) or not client_label.strip():
            raise PermissionError("client_label_required")
        if len(client_label.encode("utf-8")) > 256:
            raise ValueError("client_label_too_large")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("browser_input_required")
        if len(text.encode("utf-8")) > 8192:
            raise ValueError("browser_input_too_large")

        execution_id = execution_id or uuid4().hex
        task = TaskSpec(
            task_id="browser:" + execution_id,
            task_type="browser_request",
            objective=text.strip(),
            input=text,
            constraints={
                "_noryx7_origin": "noryx-browser",
                "_noryx7_client_label": client_label,
                "_noryx7_identity_assurance": "bootstrap_bearer_only",
            },
            verification_requirements=("runtime_result",),
            risk_class="normal",
            execution_id=execution_id,
        )

        self.runtime.heartbeat_agents()
        result = self.runtime.run_hypersynth(task)
        if not isinstance(result, dict):
            raise RuntimeError("runtime_result_malformed")
        if result.get("status") != "completed":
            verification = result.get("verification")
            reason = getattr(verification, "reason", None) or result.get("reason") or "runtime_rejected"
            raise PermissionError(str(reason))

        answer = result.get("result")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("runtime_answer_invalid")
        verification = result.get("verification")
        if not getattr(verification, "valid", False):
            raise PermissionError("runtime_result_unverified")

        return {
            "status": "completed",
            "task_id": result.get("task_id"),
            "execution_id": result.get("execution_id"),
            "result": answer,
            "verification": {
                "stage": getattr(verification, "stage", ""),
                "valid": bool(getattr(verification, "valid", False)),
                "reason": getattr(verification, "reason", ""),
            },
        }
