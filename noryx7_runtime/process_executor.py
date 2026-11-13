"""Killable process-backed adapter for trusted, importable execution handlers.

This is process isolation and timeout enforcement, NOT an OS security sandbox.
Handlers run with the same user privileges as the parent and must be trusted.
"""
from __future__ import annotations

import json
import multiprocessing
from multiprocessing.connection import Connection
from typing import Any, Callable

from .contracts import ActionEnvelope


class ProcessExecutionError(RuntimeError):
    pass


class ProcessExecutionTimeout(TimeoutError):
    pass


def _process_worker(send_conn: Connection, handler: Callable[[ActionEnvelope], Any], envelope: ActionEnvelope) -> None:
    try:
        result = handler(envelope)
        try:
            payload = json.dumps(
                {"ok": True, "result": result},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            payload = b'{"error":"result_not_json_serializable","ok":false}'
        send_conn.send_bytes(payload)
    except BaseException as exc:
        # Do not serialize exception messages, tracebacks, or arbitrary objects.
        payload = json.dumps(
            {"ok": False, "error": type(exc).__name__},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        try:
            send_conn.send_bytes(payload)
        except (BrokenPipeError, OSError):
            pass
    finally:
        send_conn.close()


class ProcessExecutionAdapter:
    """Run a trusted picklable handler in a killable spawned child process."""

    def __init__(
        self,
        handler: Callable[[ActionEnvelope], Any],
        *,
        agent_id: str,
        timeout_seconds: float = 30.0,
        terminate_grace_seconds: float = 0.25,
        max_result_bytes: int = 1_048_576,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler_must_be_callable")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id_required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds_must_be_positive")
        if isinstance(terminate_grace_seconds, bool) or not isinstance(terminate_grace_seconds, (int, float)) or terminate_grace_seconds < 0:
            raise ValueError("terminate_grace_seconds_invalid")
        if isinstance(max_result_bytes, bool) or not isinstance(max_result_bytes, int) or max_result_bytes < 1:
            raise ValueError("max_result_bytes_invalid")
        self._handler = handler
        self.agent_id = agent_id
        self.timeout_seconds = float(timeout_seconds)
        self.terminate_grace_seconds = float(terminate_grace_seconds)
        self.max_result_bytes = max_result_bytes

    def execute(self, envelope: ActionEnvelope) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope_must_be_ActionEnvelope")
        context = multiprocessing.get_context("spawn")
        receive_conn, send_conn = context.Pipe(duplex=False)
        process = context.Process(
            target=_process_worker,
            args=(send_conn, self._handler, envelope),
            daemon=True,
        )
        try:
            process.start()
            send_conn.close()
            if not receive_conn.poll(self.timeout_seconds):
                self._stop(process)
                raise ProcessExecutionTimeout("executor_deadline_exceeded")
            try:
                raw = receive_conn.recv_bytes(self.max_result_bytes)
            except (EOFError, OSError) as exc:
                self._stop(process)
                raise ProcessExecutionError("executor_process_lost") from exc
            process.join(self.terminate_grace_seconds)
            if process.is_alive():
                self._stop(process)
                raise ProcessExecutionError("executor_did_not_exit_after_result")
            try:
                response = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProcessExecutionError("executor_response_invalid") from exc
            if not isinstance(response, dict) or response.get("ok") not in (True, False):
                raise ProcessExecutionError("executor_response_schema_invalid")
            if response["ok"] is False:
                error = response.get("error")
                if not isinstance(error, str) or set(response) != {"ok", "error"}:
                    raise ProcessExecutionError("executor_error_schema_invalid")
                raise ProcessExecutionError("executor_handler_failed:" + error)
            if set(response) != {"ok", "result"}:
                raise ProcessExecutionError("executor_success_schema_invalid")
            return response["result"]
        finally:
            receive_conn.close()
            if process.pid is not None and process.is_alive():
                self._stop(process)
            if process.pid is not None:
                process.close()

    def _stop(self, process: multiprocessing.Process) -> None:
        if process.is_alive():
            process.terminate()
            process.join(self.terminate_grace_seconds)
        if process.is_alive():
            process.kill()
            process.join(self.terminate_grace_seconds)
