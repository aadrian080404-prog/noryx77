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
    def stop(self, task_id: str, generation: int) -> None:
        """Idempotent drain. A failed external stop remains durably pending."""
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
                self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
            # External process control happens only after the durable stop intent.
            # The adapter must make stop(task_id, generation) idempotent because
            # another process may retry the same pending intent after a crash.
            self._executor.stop(task_id, generation)
            self._db.execute("BEGIN IMMEDIATE")
            try:
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
