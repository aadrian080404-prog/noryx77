"""Killable process-backed adapter for trusted, importable execution handlers.

This is process-tree termination and timeout enforcement, NOT an OS security
sandbox. Handlers run with the same user privileges as the parent and must be
trusted. On POSIX, the worker owns a process group so timeout cleanup can also
terminate subprocess descendants.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import signal
import time
from multiprocessing.connection import Connection
from typing import Any, Callable

from .contracts import ActionEnvelope


class ProcessExecutionError(RuntimeError):
    pass


class ProcessExecutionTimeout(TimeoutError):
    pass


def _process_worker(
    send_conn: Connection,
    control_conn: Connection,
    handler: Callable[[ActionEnvelope], Any],
    envelope: ActionEnvelope,
) -> None:
    try:
        if os.name == "posix":
            os.setsid()
        control_conn.send_bytes(b"ready")
        result = handler(envelope)
        try:
            payload = json.dumps(
                {"ok": True, "result": result},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            payload = b'{"error":"result_not_json_serializable","ok":false}'
        send_conn.send_bytes(payload)
        # Keep the process-group leader alive until the parent has received the
        # result and can terminate any subprocesses left behind by the handler.
        try:
            control_conn.recv_bytes()
        except (EOFError, OSError):
            pass
    except BaseException as exc:
        try:
            control_conn.send_bytes(b"error")
        except (BrokenPipeError, OSError):
            pass
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
        control_conn.close()


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
        return self.execute_with_timeout(envelope, self.timeout_seconds)

    def execute_with_timeout(self, envelope: ActionEnvelope, timeout_seconds: float) -> Any:
        if not isinstance(envelope, ActionEnvelope):
            raise TypeError("envelope_must_be_ActionEnvelope")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds_must_be_positive")
        deadline = time.monotonic() + float(timeout_seconds)
        context = multiprocessing.get_context("spawn")
        receive_conn, send_conn = context.Pipe(duplex=False)
        control_parent, control_child = context.Pipe(duplex=True)
        process = context.Process(
            target=_process_worker,
            args=(send_conn, control_child, self._handler, envelope),
            daemon=True,
        )
        try:
            process.start()
            send_conn.close()
            control_child.close()
            remaining = max(0.0, deadline - time.monotonic())
            if not control_parent.poll(remaining):
                self._stop(process)
                raise ProcessExecutionTimeout("executor_deadline_exceeded")
            try:
                ready = control_parent.recv_bytes()
            except (EOFError, OSError) as exc:
                self._stop(process)
                raise ProcessExecutionError("executor_process_lost") from exc
            if ready not in (b"ready", b"error"):
                self._stop(process)
                raise ProcessExecutionError("executor_startup_handshake_invalid")
            remaining = max(0.0, deadline - time.monotonic())
            if not receive_conn.poll(remaining):
                self._stop(process)
                raise ProcessExecutionTimeout("executor_deadline_exceeded")
            try:
                raw = receive_conn.recv_bytes(self.max_result_bytes)
            except (EOFError, OSError) as exc:
                self._stop(process)
                raise ProcessExecutionError("executor_process_lost") from exc
            # The worker deliberately remains alive after sending its response.
            # Killing its process group here also removes subprocess descendants.
            self._stop(process)
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
            send_conn.close()
            control_parent.close()
            control_child.close()
            if process.pid is not None and process.is_alive():
                self._stop(process)
            if process.pid is not None:
                process.close()

    def _stop(self, process: multiprocessing.Process) -> None:
        pid = process.pid
        if pid is None:
            return
        if os.name == "posix":
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                if process.is_alive():
                    process.terminate()
            process.join(self.terminate_grace_seconds)
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                if process.is_alive():
                    process.kill()
            process.join(self.terminate_grace_seconds)
            return
        if process.is_alive():
            process.terminate()
            process.join(self.terminate_grace_seconds)
        if process.is_alive():
            process.kill()
            process.join(self.terminate_grace_seconds)
