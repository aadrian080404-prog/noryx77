from __future__ import annotations

from urllib.parse import urlsplit
from uuid import uuid4

from core.contracts import TaskSpec
from core.memory import MemoryItem
from core.operational_runtime import OperationalNORYXRuntime
from core.system_identity import CANONICAL_SYSTEM_IDENTITY


class RuntimeAdapter:
    """Translate an authenticated gateway request into the canonical operational runtime."""
    MAX_INPUT_BYTES = 8192
    SUPPORTED_CAPABILITIES = frozenset({"web_research"})

    def __init__(self, runtime: OperationalNORYXRuntime):
        required = ("heartbeat_agents", "run_hypersynth")
        if runtime is None or any(not callable(getattr(runtime, name, None)) for name in required):
            raise TypeError("operational_runtime_required")
        self.runtime = runtime

    @staticmethod
    def _validate_client_id(client_id: str) -> str:
        if not isinstance(client_id, str) or not client_id.strip():
            raise PermissionError("client_identity_required")
        if len(client_id.encode("utf-8")) > 256:
            raise ValueError("client_identity_too_large")
        return client_id.strip()

    @staticmethod
    def _validate_session_id(session_id: str | None) -> str | None:
        if session_id is None:
            return None
        if not isinstance(session_id, str) or not session_id.strip():
            raise PermissionError("authenticated_session_required")
        if len(session_id.encode("utf-8")) > 256:
            raise ValueError("session_identity_too_large")
        return session_id.strip()

    @classmethod
    def _validate_capability(cls, capability: str | None) -> str | None:
        if capability is None:
            return None
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability_invalid")
        normalized = capability.strip().lower()
        if normalized not in cls.SUPPORTED_CAPABILITIES:
            raise PermissionError("capability_not_supported")
        return normalized

    @classmethod
    def _build_task(cls, *, client_id: str, text: str, execution_id: str, capability: str | None = None, query: str | None = None) -> TaskSpec:
        task_type = capability or "browser_request"
        objective = (query or text).strip()
        constraints = {
            "_noryx7_origin": "noryx-browser",
            "_noryx7_client_id": client_id,
            "_noryx7_execution_id": execution_id,
            "_noryx7_system_id": CANONICAL_SYSTEM_IDENTITY.system_id,
            "_noryx7_creator": CANONICAL_SYSTEM_IDENTITY.creator,
        }
        if capability is not None:
            constraints["_noryx7_capability"] = capability
            if query is not None:
                constraints["query"] = query
        return TaskSpec(
            "browser:" + execution_id,
            task_type,
            objective,
            text,
            constraints,
            ("runtime_result",),
            "normal",
            execution_id,
        )

    def _record_gateway_phase(self, task, client_id, phase, metadata):
        system_fabric = getattr(self.runtime, "system_fabric", None)
        if system_fabric is not None:
            system_fabric.record_execution(execution_id=task.execution_id, client_id=client_id, phase=phase, metadata=metadata)

    def _remember_input(self, task, client_id, session_id=None, capability=None):
        memory = getattr(self.runtime, "memory", None)
        system_fabric = getattr(self.runtime, "system_fabric", None)
        if session_id is not None:
            if system_fabric is None:
                raise PermissionError("system_fabric_required")
            authorization = system_fabric.authorize(session_id, "execute")
            if authorization.identity_id != client_id:
                raise PermissionError("session_client_identity_mismatch")
            if capability is not None:
                system_fabric.authorize(session_id, capability)
        elif system_fabric is not None:
            capabilities = ("execute", capability) if capability is not None else ("execute",)
            system_fabric.bind_session(session_id=f"client:{client_id}", client_id=client_id, device_id="gateway", role="client", capabilities=capabilities)
            system_fabric.authorize(f"client:{client_id}", "execute")
            if capability is not None:
                system_fabric.authorize(f"client:{client_id}", capability)
        if memory is not None:
            memory.put(MemoryItem(memory_id=f"gateway:{task.execution_id}:input", content=task.input, kind="working", source=task.task_id, importance=0.4, execution_id=task.execution_id))
        self._record_gateway_phase(task, client_id, "gateway_received", {"task_id": task.task_id, "capability": capability or "default"})
        audit = getattr(self.runtime, "audit", None)
        if audit is not None:
            audit.record("gateway_input_bound", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, system_id=CANONICAL_SYSTEM_IDENTITY.system_id, creator=CANONICAL_SYSTEM_IDENTITY.creator, memory_id=f"gateway:{task.execution_id}:input" if memory is not None else None, capability=capability or "default")

    def _remember_output(self, task, output, client_id):
        memory = getattr(self.runtime, "memory", None)
        if memory is None:
            return
        try:
            memory.put(MemoryItem(memory_id=f"gateway:{task.execution_id}:output", content=output, kind="working", source=task.task_id, importance=0.7, execution_id=task.execution_id))
            self._record_gateway_phase(task, client_id, "gateway_completed", {"task_id": task.task_id, "verified": True})
            audit = getattr(self.runtime, "audit", None)
            if audit is not None:
                audit.record("gateway_output_bound", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, system_id=CANONICAL_SYSTEM_IDENTITY.system_id, creator=CANONICAL_SYSTEM_IDENTITY.creator, memory_id=f"gateway:{task.execution_id}:output")
        except Exception as exc:
            audit = getattr(self.runtime, "audit", None)
            if audit is not None:
                audit.record("gateway_output_memory_degraded", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, reason=type(exc).__name__)

    def _reject(self, task, client_id, reason):
        self._record_gateway_phase(task, client_id, "gateway_rejected", {"task_id": task.task_id, "reason": reason})
        audit = getattr(self.runtime, "audit", None)
        if audit is not None:
            audit.record("gateway_execution_rejected", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, reason=reason)

    def _fallback_deterministic(self, task, client_id, original_reason):
        """Retry ordinary requests through the verified local deterministic agent.

        This is deliberately unavailable to explicit capabilities such as web_research.
        It never bypasses the runtime pipeline, identity, authorization or verification.
        """
        if original_reason != "execution_failure":
            return None
        audit = getattr(self.runtime, "audit", None)
        try:
            fallback = self.runtime.run(task, agent_id="deterministic")
        except Exception as exc:
            if audit is not None:
                audit.record("gateway_deterministic_fallback_failed", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, reason=type(exc).__name__)
            return None
        if not isinstance(fallback, dict) or fallback.get("status") != "completed":
            if audit is not None:
                audit.record("gateway_deterministic_fallback_rejected", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, reason=str(fallback.get("reason", "fallback_rejected")) if isinstance(fallback, dict) else "malformed_fallback")
            return None
        verification = fallback.get("verification")
        if not getattr(verification, "valid", False):
            if audit is not None:
                audit.record("gateway_deterministic_fallback_unverified", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, reason=str(getattr(verification, "reason", "invalid_verification")))
            return None
        if fallback.get("task_id") != task.task_id or fallback.get("execution_id") != task.execution_id:
            if audit is not None:
                audit.record("gateway_deterministic_fallback_identity_mismatch", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id)
            return None
        if audit is not None:
            audit.record("gateway_deterministic_fallback_admitted", task_id=task.task_id, execution_id=task.execution_id, client_id=client_id, original_reason=original_reason, agent_id="deterministic", verification_stage=getattr(verification, "stage", ""))
        self._record_gateway_phase(task, client_id, "gateway_fallback_committed", {"task_id": task.task_id, "agent_id": "deterministic", "verified": True})
        return fallback

    @staticmethod
    def _answer_from_output(output, capability: str | None) -> str | None:
        """Convert structured capability output to the gateway's string result contract."""
        if isinstance(output, str):
            return output.strip() or None
        if capability != "web_research" or not isinstance(output, dict):
            return None
        evidence = output.get("evidence")
        results = output.get("results")
        item = evidence[0] if isinstance(evidence, list) and evidence else None
        if not isinstance(item, dict):
            item = results[0] if isinstance(results, list) and results and isinstance(results[0], dict) else None
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        domain = urlsplit(url).netloc
        snippet = str(item.get("snippet") or "").strip()
        if not title or not domain or not snippet:
            return None
        return f"Titolo: {title}\nDominio: {domain}\nSintesi: {snippet}"

    def execute(self, *, client_id, text, execution_id=None, session_id=None, capability=None, query=None):
        client_id = self._validate_client_id(client_id)
        session_id = self._validate_session_id(session_id)
        capability = self._validate_capability(capability)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("browser_input_required")
        if len(text.encode("utf-8")) > self.MAX_INPUT_BYTES:
            raise ValueError("browser_input_too_large")
        if query is not None and (not isinstance(query, str) or not query.strip()):
            raise ValueError("capability_query_invalid")
        if query is not None and len(query.encode("utf-8")) > self.MAX_INPUT_BYTES:
            raise ValueError("capability_query_too_large")
        execution_id = execution_id or uuid4().hex
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id_required")
        if len(execution_id.encode("utf-8")) > 256:
            raise ValueError("execution_id_too_large")
        task = self._build_task(client_id=client_id, text=text, execution_id=execution_id, capability=capability, query=query)
        self._remember_input(task, client_id, session_id, capability)
        try:
            self.runtime.heartbeat_agents()
            result = self.runtime.run_hypersynth(task)
        except Exception as exc:
            reason = f"runtime_exception:{type(exc).__name__}"
            self._reject(task, client_id, reason)
            raise
        if not isinstance(result, dict):
            self._reject(task, client_id, "runtime_result_malformed")
            raise RuntimeError("runtime_result_malformed")
        if result.get("status") != "completed":
            verification = result.get("verification")
            reason = str(getattr(verification, "reason", None) or result.get("reason") or "runtime_rejected")
            fallback = None if capability is not None else self._fallback_deterministic(task, client_id, reason)
            if fallback is not None:
                result = fallback
            else:
                self._reject(task, client_id, reason)
                raise PermissionError(reason)
        result_task_id = result.get("task_id") or task.task_id
        result_execution_id = result.get("execution_id") or task.execution_id
        if result_task_id != task.task_id or result_execution_id != task.execution_id:
            self._reject(task, client_id, "runtime_result_identity_mismatch")
            raise PermissionError("runtime_result_identity_mismatch")
        kernel_results = result.get("results")
        raw_answer = result.get("result")
        if raw_answer is None and isinstance(kernel_results, (tuple, list)) and kernel_results:
            raw_answer = getattr(kernel_results[-1], "output", None)
        answer = self._answer_from_output(raw_answer, capability)
        if answer is None:
            self._reject(task, client_id, "runtime_answer_invalid")
            raise RuntimeError("runtime_answer_invalid")
        verification = result.get("verification")
        if not getattr(verification, "valid", False):
            self._reject(task, client_id, "runtime_result_unverified")
            raise PermissionError("runtime_result_unverified")
        model_execution = {}
        if isinstance(kernel_results, (tuple, list)) and kernel_results:
            agent_id = getattr(kernel_results[-1], "agent_id", "")
            router = getattr(self.runtime, "router", None)
            if router is not None:
                try:
                    selected_agent = router.get(agent_id)
                    metadata = getattr(selected_agent, "last_model_execution", None)
                    if isinstance(metadata, dict):
                        model_execution = {str(key): str(value) for key, value in metadata.items() if isinstance(key, str) and isinstance(value, str)}
                except Exception:
                    model_execution = {}
        self._remember_output(task, answer, client_id)
        response = {"status": "completed", "system_id": CANONICAL_SYSTEM_IDENTITY.system_id, "creator": CANONICAL_SYSTEM_IDENTITY.creator, "task_id": result_task_id, "execution_id": result_execution_id, "client_id": client_id, "result": answer, "verification": {"stage": getattr(verification, "stage", ""), "valid": bool(getattr(verification, "valid", False)), "reason": getattr(verification, "reason", "")}}
        if capability is not None:
            response["capability"] = capability
        if model_execution:
            response["model_execution"] = model_execution
        return response
