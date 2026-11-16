"""Target-side generation fence for local Matrix process executors.

This serializes grant checks and executor calls on the target node. The wrapped
executor must itself be a trusted local process-control adapter. This module is
not an OS sandbox and cannot prove process termination after host compromise.
"""
from __future__ import annotations

import sqlite3
from threading import RLock
from typing import Protocol

from .matrix_core import WorkloadRequest


class TargetExecutor(Protocol):
    def start(self, request: WorkloadRequest, generation: int) -> None: ...
    def stop(self, task_id: str, generation: int) -> None: ...


class TargetFenceError(PermissionError):
    pass


class SQLiteGenerationFencedExecutor:
    """Serialize local starts/stops with durable grant generations.

    All executor calls run while a SQLite IMMEDIATE transaction is held. This
    deliberately trades throughput for a single target-side ordering point:
    a revoke cannot pass a start that has already entered the executor, and a
    stale start cannot pass a committed revoke. The executor calls therefore
    must be local, bounded process-control operations, never arbitrary agent code.
    """

    def __init__(self, database_path: str, node_id: str, executor: TargetExecutor,
                 *, busy_timeout_ms: int = 5000) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("target_fence_database_path_required")
        if not isinstance(node_id, str) or not node_id.strip() or len(node_id.encode("utf-8")) > 256:
            raise ValueError("target_fence_node_id_invalid")
        if not callable(getattr(executor, "start", None)) or not callable(getattr(executor, "stop", None)):
            raise TypeError("target_executor_contract_required")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or not 1 <= busy_timeout_ms <= 60000:
            raise ValueError("target_fence_busy_timeout_invalid")
        self.node_id = node_id
        self._executor = executor
        self._lock = RLock()
        self._db = sqlite3.connect(
            database_path, timeout=busy_timeout_ms / 1000,
            isolation_level=None, check_same_thread=False,
        )
        self._db.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA trusted_schema=OFF")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS matrix_target_grants (
                node_id TEXT PRIMARY KEY,
                generation INTEGER NOT NULL CHECK(generation >= 0),
                enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS matrix_target_executions (
                node_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                generation INTEGER NOT NULL CHECK(generation >= 0),
                state TEXT NOT NULL CHECK(state IN ('running','stop_pending')),
                PRIMARY KEY(node_id, task_id)
            )
        """)
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("target_fence_closed")

    def apply_grant(self, generation: int, *, enabled: bool) -> None:
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("target_fence_generation_invalid")
        if not isinstance(enabled, bool):
            raise ValueError("target_fence_enabled_must_be_boolean")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT generation,enabled FROM matrix_target_grants WHERE node_id=?",
                    (self.node_id,),
                ).fetchone()
                if row is None:
                    self._db.execute(
                        "INSERT INTO matrix_target_grants(node_id,generation,enabled) VALUES(?,?,?)",
                        (self.node_id, generation, int(enabled)),
                    )
                else:
                    current_generation, current_enabled = int(row[0]), bool(row[1])
                    if generation < current_generation:
                        raise TargetFenceError("stale_target_grant_generation")
                    if generation == current_generation and enabled and not current_enabled:
                        raise TargetFenceError("revoked_generation_cannot_reactivate")
                    if generation == current_generation and enabled == current_enabled:
                        self._db.execute("COMMIT")
                        return
                    self._db.execute(
                        "UPDATE matrix_target_grants SET generation=?,enabled=? WHERE node_id=?",
                        (generation, int(enabled), self.node_id),
                    )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def start(self, request: WorkloadRequest, generation: int) -> None:
        if not isinstance(request, WorkloadRequest):
            raise TypeError("workload_request_required")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("target_fence_generation_invalid")
        if request.generation != generation:
            raise TargetFenceError("request_generation_mismatch")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                grant = self._db.execute(
                    "SELECT generation,enabled FROM matrix_target_grants WHERE node_id=?",
                    (self.node_id,),
                ).fetchone()
                if grant is None or int(grant[0]) != generation or int(grant[1]) != 1:
                    raise TargetFenceError("target_grant_not_active_for_generation")
                existing = self._db.execute(
                    "SELECT generation,state FROM matrix_target_executions WHERE node_id=? AND task_id=?",
                    (self.node_id, request.task_id),
                ).fetchone()
                if existing is not None:
                    if int(existing[0]) != generation:
                        raise TargetFenceError("task_id_generation_conflict")
                    if existing[1] == "running":
                        self._db.execute("COMMIT")
                        return
                    raise TargetFenceError("task_stop_pending")
                self._db.execute(
                    "INSERT INTO matrix_target_executions(node_id,task_id,generation,state) VALUES(?,?,?,'running')",
                    (self.node_id, request.task_id, generation),
                )
                self._executor.start(request, generation)
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def stop(self, task_id: str, generation: int) -> None:
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id.encode("utf-8")) > 256:
            raise ValueError("target_fence_task_id_invalid")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("target_fence_generation_invalid")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT generation,state FROM matrix_target_executions WHERE node_id=? AND task_id=?",
                    (self.node_id, task_id),
                ).fetchone()
                if row is None:
                    self._db.execute("COMMIT")
                    return
                if int(row[0]) != generation:
                    raise TargetFenceError("stop_generation_mismatch")
                self._db.execute(
                    "UPDATE matrix_target_executions SET state='stop_pending' WHERE node_id=? AND task_id=?",
                    (self.node_id, task_id),
                )
                self._executor.stop(task_id, generation)
                self._db.execute(
                    "DELETE FROM matrix_target_executions WHERE node_id=? AND task_id=? AND generation=?",
                    (self.node_id, task_id, generation),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def pending(self) -> tuple[tuple[str, int, str], ...]:
        with self._lock:
            self._ensure_open()
            rows = self._db.execute(
                "SELECT task_id,generation,state FROM matrix_target_executions WHERE node_id=? ORDER BY task_id",
                (self.node_id,),
            ).fetchall()
            return tuple((row[0], int(row[1]), row[2]) for row in rows)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
