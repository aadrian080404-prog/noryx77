"""Durable target-side generation fencing for trusted local Matrix executors.

SQLite orders grant changes and starts on one target node. The wrapped executor
must be a trusted local process supervisor with idempotent, per-task start/stop
semantics so ambiguous calls can be safely reconciled after a crash.
This is not an OS sandbox, distributed consensus, or proof of process death.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from threading import RLock
from typing import Protocol

from .matrix_core import WorkloadRequest


class TargetExecutor(Protocol):
    def start(self, request: WorkloadRequest, generation: int) -> None:
        """Idempotently ensure this task/generation is running."""
        ...

    def stop(self, task_id: str, generation: int) -> None:
        """Idempotently ensure this task/generation is stopped."""
        ...


class TargetFenceError(RuntimeError):
    """A target-side grant or execution fence rejected an operation."""


class SQLiteGenerationFencedExecutor:
    def __init__(self, database_path: str, node_id: str, executor: TargetExecutor) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("database_path_required")
        if not isinstance(node_id, str) or not node_id.strip() or len(node_id.encode("utf-8")) > 256:
            raise ValueError("node_id_invalid")
        if executor is None or not callable(getattr(executor, "start", None)) or not callable(getattr(executor, "stop", None)):
            raise TypeError("target_executor_invalid")
        self.node_id = node_id
        self._executor = executor
        self._lock = RLock()
        self._closed = False
        self._db = sqlite3.connect(database_path, timeout=10.0, isolation_level=None, check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA busy_timeout=10000")
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS matrix_target_grants (
                    node_id TEXT PRIMARY KEY,
                    generation INTEGER NOT NULL CHECK(generation >= 0),
                    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS matrix_target_executions (
                    node_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation >= 0),
                    request_digest TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('starting', 'running', 'stop_pending')),
                    PRIMARY KEY(node_id, task_id)
                );
            """)
            schema = self._db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='matrix_target_executions'"
            ).fetchone()
            if schema is not None and "'starting'" not in (schema[0] or ""):
                # Upgrade databases created by the first draft of this adapter,
                # whose CHECK constraint did not yet include the durable
                # pre-launch state. Preserve every existing execution row.
                self._db.execute("BEGIN IMMEDIATE")
                try:
                    self._db.execute(
                        "ALTER TABLE matrix_target_executions RENAME TO matrix_target_executions_legacy"
                    )
                    self._db.execute("""
                        CREATE TABLE matrix_target_executions (
                            node_id TEXT NOT NULL,
                            task_id TEXT NOT NULL,
                            generation INTEGER NOT NULL CHECK(generation >= 0),
                            request_digest TEXT NOT NULL,
                            state TEXT NOT NULL CHECK(state IN ('starting', 'running', 'stop_pending')),
                            PRIMARY KEY(node_id, task_id)
                        )
                    """)
                    self._db.execute(
                        "INSERT INTO matrix_target_executions(node_id,task_id,generation,request_digest,state) "
                        "SELECT node_id,task_id,generation,request_digest,state "
                        "FROM matrix_target_executions_legacy"
                    )
                    self._db.execute("DROP TABLE matrix_target_executions_legacy")
                    self._db.execute("COMMIT")
                except Exception:
                    if self._db.in_transaction:
                        self._db.execute("ROLLBACK")
                    raise
        except Exception:
            self._db.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("target_fence_closed")

    @staticmethod
    def _validate_generation(generation: int) -> None:
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("target_fence_generation_invalid")

    @staticmethod
    def _request_digest(request: WorkloadRequest) -> str:
        resources = request.resources
        payload = {
            "task_id": request.task_id,
            "workload_class": request.workload_class,
            "generation": request.generation,
            "resources": {
                "cpu_milli": resources.cpu_milli,
                "memory_bytes": resources.memory_bytes,
                "storage_bytes": resources.storage_bytes,
                "bandwidth_bps": resources.bandwidth_bps,
            },
            "requires_attestation": request.requires_attestation,
            "requires_sandbox": request.requires_sandbox,
            "requires_user_data": request.requires_user_data,
            "allowed_failure_domains": sorted(request.allowed_failure_domains),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def apply_grant(self, generation: int, *, enabled: bool) -> None:
        self._validate_generation(generation)
        if not isinstance(enabled, bool):
            raise ValueError("target_fence_enabled_must_be_boolean")
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT generation, enabled FROM matrix_target_grants WHERE node_id=?",
                    (self.node_id,),
                ).fetchone()
                if row is not None:
                    old_generation, old_enabled = int(row[0]), bool(row[1])
                    if generation < old_generation:
                        raise TargetFenceError("grant_generation_stale")
                    if generation == old_generation and old_enabled is False and enabled is True:
                        raise TargetFenceError("grant_generation_cannot_reactivate")
                    if generation == old_generation and old_enabled is True and enabled is False:
                        # Same-epoch revocation is allowed; re-enabling that epoch is not.
                        pass
                self._db.execute(
                    "INSERT INTO matrix_target_grants(node_id,generation,enabled) VALUES(?,?,?) "
                    "ON CONFLICT(node_id) DO UPDATE SET generation=excluded.generation, enabled=excluded.enabled",
                    (self.node_id, generation, int(enabled)),
                )
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def start(self, request: WorkloadRequest, generation: int) -> None:
        if not isinstance(request, WorkloadRequest):
            raise TypeError("workload_request_required")
        self._validate_generation(generation)
        if not isinstance(request.task_id, str) or not request.task_id.strip() or len(request.task_id.encode("utf-8")) > 256:
            raise ValueError("target_fence_task_id_invalid")
        if request.generation != generation:
            raise TargetFenceError("request_generation_mismatch")
        digest = self._request_digest(request)
        with self._lock:
            self._ensure_open()
            try:
                # BEGIN IMMEDIATE serializes grant changes and starts even across
                # independent SQLite connections on this target node.
                self._db.execute("BEGIN IMMEDIATE")
                grant = self._db.execute(
                    "SELECT generation, enabled FROM matrix_target_grants WHERE node_id=?",
                    (self.node_id,),
                ).fetchone()
                if grant is None or int(grant[0]) != generation or int(grant[1]) != 1:
                    raise TargetFenceError("grant_not_active_for_generation")
                existing = self._db.execute(
                    "SELECT generation, request_digest, state FROM matrix_target_executions "
                    "WHERE node_id=? AND task_id=?",
                    (self.node_id, request.task_id),
                ).fetchone()
                if existing is not None:
                    if int(existing[0]) != generation or existing[1] != digest:
                        raise TargetFenceError("task_identity_conflict")
                    if existing[2] == "running":
                        self._db.execute("COMMIT")
                        return
                    if existing[2] == "stop_pending":
                        raise TargetFenceError("task_stop_pending")
                    # 'starting' is a durable intent left by an interrupted or
                    # ambiguous launch. Retry through the idempotent supervisor.
                else:
                    self._db.execute(
                        "INSERT INTO matrix_target_executions(node_id,task_id,generation,request_digest,state) "
                        "VALUES(?,?,?,?, 'starting')",
                        (self.node_id, request.task_id, generation, digest),
                    )
                # Commit the start intent BEFORE calling the process supervisor.
                # A crash or ambiguous return therefore leaves a recoverable row.
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

            # Re-acquire the SQLite write lock and re-check the grant immediately
            # before process control. Revocation cannot race this bounded call.
            # The earlier committed 'starting' row survives rollback/crash.
            try:
                self._db.execute("BEGIN IMMEDIATE")
                grant = self._db.execute(
                    "SELECT generation, enabled FROM matrix_target_grants WHERE node_id=?",
                    (self.node_id,),
                ).fetchone()
                if grant is None or int(grant[0]) != generation or int(grant[1]) != 1:
                    raise TargetFenceError("grant_revoked_before_launch")
                # The target supervisor must make start(task_id,generation)
                # idempotent and linearizable with stop for this task.
                self._executor.start(request, generation)
                cursor = self._db.execute(
                    "UPDATE matrix_target_executions SET state='running' "
                    "WHERE node_id=? AND task_id=? AND generation=? "
                    "AND request_digest=? AND state='starting'",
                    (self.node_id, request.task_id, generation, digest),
                )
                if cursor.rowcount != 1:
                    raise TargetFenceError("start_intent_changed_during_launch")
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def stop(self, task_id: str, generation: int) -> None:
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id.encode("utf-8")) > 256:
            raise ValueError("target_fence_task_id_invalid")
        self._validate_generation(generation)
        with self._lock:
            self._ensure_open()
            try:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._db.execute(
                    "SELECT generation FROM matrix_target_executions WHERE node_id=? AND task_id=?",
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
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

            # The durable stop intent is committed before external process control.
            # The supervisor must serialize start/stop per task and make stop idempotent.
            self._executor.stop(task_id, generation)
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "DELETE FROM matrix_target_executions WHERE node_id=? AND task_id=? "
                    "AND generation=? AND state='stop_pending'",
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
                "SELECT task_id,generation,state FROM matrix_target_executions "
                "WHERE node_id=? ORDER BY task_id",
                (self.node_id,),
            ).fetchall()
            return tuple((row[0], int(row[1]), row[2]) for row in rows)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True

    def __enter__(self) -> "SQLiteGenerationFencedExecutor":
        with self._lock:
            self._ensure_open()
            return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.close()
        return False
