import sqlite3
import threading

import pytest

from core.matrix_core import ResourceVector, WorkloadRequest
from core.matrix_target_fence import SQLiteGenerationFencedExecutor, TargetFenceError


class Executor:
    def __init__(self):
        self.started = []
        self.stopped = []
        self.fail_start = False
        self.fail_stop = False

    def start(self, request, generation):
        if self.fail_start:
            raise RuntimeError("start_failed")
        self.started.append((request.task_id, generation))

    def stop(self, task_id, generation):
        if self.fail_stop:
            raise RuntimeError("stop_failed")
        self.stopped.append((task_id, generation))


def request(task_id="task-1", generation=4):
    return WorkloadRequest(
        task_id, "compute", ResourceVector(100, 1024), generation,
        requires_attestation=False, requires_sandbox=False,
    )


def test_target_fence_requires_current_enabled_grant(tmp_path):
    executor = Executor()
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", executor
    )
    try:
        with pytest.raises(TargetFenceError, match="not_active"):
            fence.start(request(), 4)
        fence.apply_grant(4, enabled=True)
        fence.start(request(), 4)
        assert executor.started == [("task-1", 4)]
    finally:
        fence.close()


def test_target_fence_start_is_idempotent_and_rejects_stale_generation(tmp_path):
    executor = Executor()
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", executor
    )
    try:
        fence.apply_grant(4, enabled=True)
        fence.start(request(), 4)
        fence.start(request(), 4)
        assert executor.started == [("task-1", 4)]
        with pytest.raises(TargetFenceError, match="not_active"):
            fence.start(request(generation=3), 3)
    finally:
        fence.close()


def test_revoked_generation_cannot_be_reenabled(tmp_path):
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", Executor()
    )
    try:
        fence.apply_grant(4, enabled=True)
        fence.apply_grant(5, enabled=False)
        with pytest.raises(TargetFenceError, match="cannot_reactivate"):
            fence.apply_grant(5, enabled=True)
        with pytest.raises(TargetFenceError, match="stale"):
            fence.apply_grant(4, enabled=True)
        fence.apply_grant(6, enabled=True)
    finally:
        fence.close()


def test_target_fence_stop_is_idempotent_and_clears_record(tmp_path):
    executor = Executor()
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", executor
    )
    try:
        fence.apply_grant(4, enabled=True)
        fence.start(request(), 4)
        fence.stop("task-1", 4)
        fence.stop("task-1", 4)
        assert executor.stopped == [("task-1", 4)]
        assert fence.pending() == ()
    finally:
        fence.close()


def test_stop_failure_keeps_durable_pending_intent_for_retry(tmp_path):
    path = str(tmp_path / "target.db")
    executor = Executor()
    fence = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    fence.apply_grant(4, enabled=True)
    fence.start(request(), 4)
    executor.fail_stop = True
    with pytest.raises(RuntimeError, match="stop_failed"):
        fence.stop("task-1", 4)
    assert fence.pending() == (("task-1", 4, "stop_pending"),)
    fence.close()

    executor.fail_stop = False
    reopened = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    try:
        reopened.stop("task-1", 4)
        assert reopened.pending() == ()
        assert executor.stopped == [("task-1", 4)]
    finally:
        reopened.close()


def test_target_fence_start_failure_does_not_leave_active_record(tmp_path):
    executor = Executor()
    executor.fail_start = True
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", executor
    )
    try:
        fence.apply_grant(4, enabled=True)
        with pytest.raises(RuntimeError, match="start_failed"):
            fence.start(request(), 4)
        assert fence.pending() == ()
    finally:
        fence.close()


def test_target_fence_rejects_wrong_stop_generation(tmp_path):
    executor = Executor()
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "target.db"), "node-1", executor
    )
    try:
        fence.apply_grant(4, enabled=True)
        fence.start(request(), 4)
        with pytest.raises(TargetFenceError, match="stop_generation_mismatch"):
            fence.stop("task-1", 5)
        assert executor.stopped == []
        assert fence.pending() == (("task-1", 4, "running"),)
    finally:
        fence.close()


def test_target_fence_serializes_concurrent_duplicate_starts(tmp_path):
    path = str(tmp_path / "target.db")
    executor = Executor()
    first = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    second = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    first.apply_grant(4, enabled=True)
    errors = []

    def run(fence):
        try:
            fence.start(request(), 4)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(first if i % 2 else second,))
               for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    try:
        assert errors == []
        assert executor.started == [("task-1", 4)]
    finally:
        first.close()
        second.close()


def test_target_fence_persists_active_generation_and_task(tmp_path):
    path = str(tmp_path / "target.db")
    executor = Executor()
    first = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    first.apply_grant(4, enabled=True)
    first.start(request(), 4)
    first.close()

    reopened = SQLiteGenerationFencedExecutor(path, "node-1", executor)
    try:
        assert reopened.pending() == (("task-1", 4, "running"),)
        reopened.apply_grant(5, enabled=False)
        with pytest.raises(TargetFenceError, match="not_active"):
            reopened.start(request("task-2", 5), 5)
    finally:
        reopened.close()


def test_target_fence_validates_node_and_lifecycle(tmp_path):
    with pytest.raises(ValueError, match="node_id"):
        SQLiteGenerationFencedExecutor(str(tmp_path / "bad.db"), " ", Executor())
    fence = SQLiteGenerationFencedExecutor(
        str(tmp_path / "closed.db"), "node-1", Executor()
    )
    fence.close()
    with pytest.raises(RuntimeError, match="closed"):
        fence.pending()
