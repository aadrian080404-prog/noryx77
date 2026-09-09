from __future__ import annotations

from uuid import uuid4

from core.contracts import TaskSpec
from core.memory import MemoryItem
from core.operational_runtime import OperationalNORYXRuntime


class RuntimeAdapter:
    """Translate an authenticated gateway request into the canonical operational runtime."""

    MAX_INPUT_BYTES = 8192

    def __init__(self, runtime: OperationalNORYXRuntime):
        if not isinstance(runtime, OperationalNORYXRuntime):
            raise TypeError("operational_runtime_required")
        self.runtime = runtime

    @staticmethod
    def _validate_client_id(client_id: str) -> str:
        if not isinstance(client_id, str) or not client_id.strip():
            raise PermissionError("client_identity_required")
        if len(client_id.encode("utf-8")) > 256:
            raise ValueError("client_identity_too_large")
        return client_id.strip()

    @classmethod
    def _build_task(cls, *, client_id: str, text: str, execution_id: str) -> TaskSpec:
        return TaskSpec(
            task_id="browser:" + execution_id,
            task_type="browser_request",
            objective=text.strip(),
            input=text,
            constraints={
                "_noryx7_origin": "noryx-browser",
                "_noryx7_client_id": client_id,
                "_noryx7_execution_id": execution_id,
            },
            verification_requirements=("runtime_result",),
            risk_class="normal",
            execution_id=execution_id,
        )

    def _remember_input(self, task: TaskSpec, client_id: str) -> None:
        memory = getattr(self.runtime, "memory", None)
        if memory is None:
            raise RuntimeError("runtime_memory_unavailable")
        memory.put(
            MemoryItem(
                memory_id=f"gateway:{task.execution_id}:input",
                content=task.input,
                kind="working",
                source=task.task_id,
                importance=0.4,
                execution_id=task.execution_id,
            )
        )
        audit = getattr(self.runtime, "audit", None)
        if audit is not None:
            audit.record(
                "gateway_input_bound",
                task_id=task.task_id,
                execution_id=task.execution_id,
                client_id=client_id,
                memory_id=f"gateway:{task.execution_id}:input",
            )

    def _remember_output(self, task: TaskSpec, output: str, client_id: str) -> None:
        memory = getattr(self.runtime, "memory", None)
        if memory is None:
            return
        try:
            memory.put(
                MemoryItem(
                    memory_id=f"gateway:{task.execution_id}:output",
                    content=output,
                    kind="working",
                    source=task.task_id,
                    importance=0.7,
                    execution_id=task.execution_id,
                )
            )
            audit = getattr(self.runtime, "audit", None)
            if audit is not None:
                audit.record(
                    "gateway_output_bound",
                    task_id=task.task_id,
                    execution_id=task.execution_id,
                    client_id=client_id,
                    memory_id=f"gateway:{task.execution_id}:output",
                )
        except Exception as exc:
            audit = getattr(self.runtime, "audit", None)
            if audit is not None:
                audit.record(
                    "gateway_output_memory_degraded",
                    task_id=task.task_id,
                    execution_id=task.execution_id,
                    client_id=client_id,
                    reason=type(exc).__name__,
                )

    def execute(
        self,
        *,
        client_id: str,
        text: str,
        execution_id: str | None = None,
    ) -> dict:
        client_id = self._validate_client_id(client_id)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("browser_input_required")
        if len(text.encode("utf-8")) > self.MAX_INPUT_BYTES:
            raise ValueError("browser_input_too_large")

        execution_id = execution_id or uuid4().hex
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id_required")
        if len(execution_id.encode("utf-8")) > 256:
            raise ValueError("execution_id_too_large")

        task = self._build_task(
            client_id=client_id,
            text=text,
            execution_id=execution_id,
        )
        self._remember_input(task, client_id)

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

        self._remember_output(task, answer, client_id)
        return {
            "status": "completed",
            "task_id": result.get("task_id"),
            "execution_id": result.get("execution_id"),
            "client_id": client_id,
            "result": answer,
            "verification": {
                "stage": getattr(verification, "stage", ""),
                "valid": bool(getattr(verification, "valid", False)),
                "reason": getattr(verification, "reason", ""),
            },
        }
